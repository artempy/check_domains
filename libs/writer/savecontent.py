import csv
from contextlib import contextmanager
from threading import RLock
import logging


@contextmanager
def opened_w_error(filename, lock, mode="r"):
    """
    Working with a file in safe/thread-safe mode
    """
    try:
        lock.acquire()
        f = open(filename, mode)
    except IOError as err:
        yield None, err.args[1]
    else:
        try:
            yield f, None
        finally:
            f.close()
            lock.release()


class Writer(object):
    def __init__(self, filename, lock=None):
        self.filename = filename
        if lock is None:
            self.lock = RLock()
        else:
            self.lock = lock

    def write_string(self, content, delimiter="\n"):
        """
        Write one's string to file in threadsafe mode.
        """
        with opened_w_error(self.filename, self.lock, "a") as (f, err):
            if err:
                logging.error("File '%s'. Error: %s", self.filename, err)
            else:
                f.write(content + delimiter)

    @staticmethod
    def check_list_exists(this_list=[]):
        """
        Check list on exists. If variable is list and it contains more zero
        elements then return 'True'. Otherwise is 'False'
        """
        if isinstance(this_list, list) and len(this_list) > 0:
            return True
        else:
            return False

    def write_list(self, data, delimiter="\n"):
        """
        Write elements of list to file in threadsafe mode.
        """
        if self.check_list_exists(data):
            with opened_w_error(self.filename, self.lock, "a") as (f, err):
                if err:
                    logging.error("File '%s'. Error: %s", self.filename, err)
                else:
                    f.write(delimiter.join(data))
        else:
            logging.error("Data isn't list or it's not contains elements")


class WriterCSV(Writer):
    """
    WriterCSV is using for write to file of csv format.
    """
    def __init__(self, first_row=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if first_row is not None:
            self.write_string(first_row)

    def write_string(self, content, delimiter=";"):
        with opened_w_error(self.filename, self.lock, "a") as (f, err):
            if err:
                logging.error("File '%s'. Error: %s", self.filename, err)
            else:
                writer = csv.writer(
                    f,
                    delimiter=delimiter,
                    quotechar='"',
                    quoting=csv.QUOTE_ALL
                )
                writer.writerow(content)

    def write_list(self, data, delimiter=""):
        if self.check_list_exists(data):
            with opened_w_error(self.filename, self.lock, "a") as (f, err):
                if err:
                    logging.error("File '%s'. Error: %s", self.filename, err)
                else:
                    writer = csv.writer(
                        f,
                        delimiter=delimiter,
                        quotechar='"',
                        quoting=csv.QUOTE_ALL
                    )
                    for line in data:
                        writer.writerow(line)
        else:
            logging.error("Data isn't list or it's not contains elements")
