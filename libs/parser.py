import threading
import logging
from queue import Queue, Empty
from libs.curl.net import Net
from libs.curl.proxylist import ProxyList


logger = logging.getLogger('Parser')


def create_tasks(tasks=[]):
    """
    Adding tasks to a queue
    """
    queue = Queue()
    for task in tasks:
        queue.put(task)
    return queue


class Task(threading.Thread):
    def __init__(self, myargs):
        super().__init__()
        self.config = myargs['config']
        self.list_proxy = myargs['list_proxy']
        self.tasks = myargs['tasks']
        self.lock = myargs['lock']
        self.finished = myargs['finished']
        self.write_res = myargs['write_res']
        self.daemon = True

    def get_task(self):
        """
        Getting task from a queue
        """
        try:
            task = self.tasks.get_nowait()
            logger.debug('Running task: %s', task)
            return task
        except Empty:
            logger.debug('Queue tasks is empty. Stop thread!')
            return None


class CreateThreads(object):
    """
    Creating threads. Initializing Proxylist, Rlock, Event for thread-safe.
    """
    def __init__(self, config, tasks, write_res=None, cls=Task,
                 num_threads=None):
        self.config = config
        if self.config['useproxy']:
            self.list_proxy = ProxyList(self.config)
        else:
            self.list_proxy = None
        self.lock = threading.RLock()
        self.finished = threading.Event()
        self.write_res = write_res
        if num_threads is None:
            self.num_threads = config['numthreads']
        else:
            self.num_threads = num_threads
        self.tasks = create_tasks(tasks)
        self.threads = []
        for _ in range(self.num_threads):
            thread = cls({
                'config': self.config,
                'list_proxy': self.list_proxy,
                'tasks': self.tasks,
                'lock': self.lock,
                'finished': self.finished,
                'write_res': self.write_res
            })
            thread.start()
            self.threads.append(thread)

    def finish(self):
        """
        Safe complete all the threads.
        """
        logger.debug('Stopping threads!')
        self.finished.set()
        for thread in self.threads:
            thread.join()

    def is_threads(self):
        """
        Checking threads on exists.
        """
        if threading.activeCount() > 1:
            return True
        else:
            return False


class GetContent(object):
    """
    Getting page.
    """
    def __init__(self, config, list_proxy=None):
        self.list_proxy = list_proxy
        self.config = config

    def get_page(self, url):
        data = None
        for _ in range(3):
            """
            Three attempts for get page.
            """
            if self.list_proxy:
                proxy = self.list_proxy.get_proxy()
            else:
                proxy = None
            request = Net(self.config, proxy=proxy)
            data = request.get_content(url)
            if data:
                break
        return data
