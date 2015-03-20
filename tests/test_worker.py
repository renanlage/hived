import time
import unittest

from mock import call, Mock, patch, ANY

from hived.worker import BaseWorker


class BaseWorkerTest(unittest.TestCase):
    def test_bad_messages_are_thrown_out(self):
        exc = AssertionError('bad bad bad')

        class W(BaseWorker):
            def validate_message(self, body):
                # make sure it halts
                self.stopped = True
                raise exc

        queue_name = 'myqueue'
        w = W(Mock(), queue_name=queue_name)
        w.queue = Mock()
        w.queue.get.return_value = ({}, 1)

        w.run()

        self.assertEqual(w.queue.put.call_args,
                         call({'garbage_reason': str(exc)},
                              queue_name + '_garbage',
                              exchange=''))
        self.assertTrue(w.queue.ack.called)

    def test_worker_waits_before_restarting_after_a_crash(self):
        exc = AssertionError('bad bad bad')

        class W(BaseWorker):
            already_called = False

            def protected_run(self):
                # make sure it halts 
                if self.already_called:
                    self.stopped = True
                else:
                    self.already_called = True
                raise exc

        w = W(Mock(), 'myqueue')
        with patch.object(time, 'sleep') as sleep:
            w.run()
            sleep_times = [c[0][0] for c in sleep.call_args_list]
            self.assertLess(sleep_times[0], sleep_times[1])

    def test_get_task_instantiates_task_class(self):
        class W(BaseWorker):
            task_class = Mock()

        worker = W(Mock(), 'myqueue')
        message = Mock()
        task = worker.get_task(message)
        self.assertEqual(task, W.task_class.return_value)
        self.assertEqual(W.task_class.call_args_list, [call(message)])

    def test_protected_run_sends_message_to_garbage_if_validate_message_fails(self):
        class W(BaseWorker):
            def validate_message(self, message):
                self.stopped = True
                assert False

        worker = W(Mock(), 'myqueue')
        worker.queue = Mock()
        message, ack = Mock(), Mock()
        worker.queue.get.return_value = (message, ack)

        with patch.object(worker, 'send_message_to_garbage') as send_to_garbage_mock:
            worker.protected_run()
            self.assertEqual(send_to_garbage_mock.call_args_list, [call(message, ack, ANY)])

    def test_protected_run_sends_message_to_garbage_if_get_task_fails(self):
        class W(BaseWorker):
            def get_task(self, message):
                self.stopped = True
                assert False

        worker = W(Mock(), 'myqueue')
        worker.queue = Mock()
        message, ack = Mock(), Mock()
        worker.queue.get.return_value = (message, ack)

        with patch.object(worker, 'send_message_to_garbage') as send_to_garbage_mock:
            worker.protected_run()
            self.assertEqual(send_to_garbage_mock.call_args_list, [call(message, ack, ANY)])


if __name__ == '__main__':
    unittest.main()
