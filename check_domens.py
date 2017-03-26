# -*- coding: utf-8 -*-
import logging
import os.path
from time import sleep
from datetime import datetime
import urllib.parse
from libs.parser import CreateThreads, Task, GetContent
from config.config import ConfigReader
from libs.writer.savecontent import WriterCSV
from check_se.yandex import *


class MyTask(Task):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        con = GetContent(self.config, self.list_proxy)
        while not self.finished.is_set():
            """
            If Event True then to complete thread.
            """
            domain = self.get_task()
            if domain is None:
                break
            """
            Domain is checking for numbers pages
            """
            host_ya = 'https://yandex.ru/search/?'
            parameters = {
                'text': 'host:"{0}"* | host:"www.{0}"*'.format(domain)
            }
            url = host_ya + urllib.parse.urlencode(parameters)
            num_try = 0
            while num_try < self.config['numtrygetpage']:
                page = con.get_page(url)
                if page is None:
                    continue
                res = yandex_num_pages(page)
                if res is not None and res is not False:
                    num_pages = res
                    break
                num_try += 1
            else:
                num_pages = 0
            """
            Domain is checking for Index's Citation Yandex
            """
            url = 'https://yaca.yandex.ru/yca/cy/ch/%s/' % domain
            num_try = 0
            while num_try < self.config['numtrygetpage']:
                page = con.get_page(url)
                if page is None:
                    continue
                res = yandex_isnot_filter_tic(page)
                """
                If index's citation was defined
                """
                if res is not None and res is not False:
                    tic = res
                    break
                elif res is False:
                    tic = False
                    break
                num_try += 1
            else:
                tic = False
            """
            Domain is checking for glue domain with another a domain
            """
            host_ya = 'http://bar-navig.yandex.ru/u?'
            parameters = {'ver': '2',
                          'url': 'http://' + domain,
                          'show': '1',
                          'post': '0'
                          }
            url = host_ya + urllib.parse.urlencode(parameters)
            num_try = 0
            while num_try < self.config['numtrygetpage']:
                page = con.get_page(url)
                if page is None:
                    continue
                res = yandex_isnot_glue(page, domain)
                if res is not None:
                    isnot_glue = res
                    break
                num_try += 1
            else:
                isnot_glue = False
            """
            If index's citation is undefined
            """
            if tic is False or tic is None:
                tic_save = -1
            else:
                tic_save = tic
            """
            Saving data
            """
            data_csv = [
                domain,
                str(num_pages),
                str(tic_save),
                str(isnot_glue)
            ]
            if isnot_glue and tic is not False and tic is not None:
                self.write_res['ok'].write_string(data_csv)
                logging.debug("Good domain '%s' has been saved" % domain)
            else:
                self.write_res['filter'].write_string(data_csv)
                logging.debug("Bad domain '%s' has been saved" % domain)


if __name__ == "__main__":
    config_obj = ConfigReader()
    config_obj.types_params = {"listproxiesurl": 'str',
                               "listproxiesfile": 'str',
                               "numattemptloadproxies": 'int',
                               "sleepattemptloadproxies": 'int',
                               "urlforcheckproxy": 'str',
                               "searchwordcheckproxy": 'str',
                               "periodproxyupdate": 'int',
                               "useproxy": 'bool',
                               "autoreferer": 'bool',
                               "usecookies": 'bool',
                               "maindebug": 'bool',
                               "debug": 'bool',
                               "timeout": 'int',
                               "maxredirs": 'int',
                               "connecttimeout": 'int',
                               "typeproxy": 'str',
                               "checkproxy": 'bool',
                               "numattemptcheckproxy": 'int',
                               "numthreads": 'int',
                               "numtrygetpage": 'int'
                               }
    config = config_obj.config_read("config/my.ini")
    """
    Name of directory is setting for save results
    """
    dir_with_date = "{0}-{1}-{2}_{3}-{4}".format(
        datetime.now().day,
        datetime.now().month,
        datetime.now().year,
        datetime.now().hour,
        datetime.now().minute
    )
    dir_name = os.path.join('results', dir_with_date)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    if config['maindebug']:
        dir_log = os.path.join('logs', dir_with_date)
        if not os.path.exists(dir_log):
            os.makedirs(dir_log)
        format = "'%(filename)s[LINE:%(lineno)d]#%(levelname)-8s [%(asctime)s] \
        %(message)s'"
        logging.basicConfig(
            format=format,
            level=logging.DEBUG,
            filename=dir_log + '/log.txt'
        )
    """
    Reading text file with list of domens
    """
    with open('domens.txt', 'r') as f:
        lines = f.readlines()
        tasks = [line.strip() for line in lines]
    if len(tasks) < 1:
        logging.error("List tasks is empty! Terminate...")
    else:
        """
        Setting first row in csv file
        """
        first_row = [
            'DOMAIN',
            'NUMBER PAGES',
            'TIC',
            'IS_NOT_GLUE'
        ]
        csv_ok = WriterCSV(filename=dir_name + '/ok.csv', first_row=first_row)
        csv_filter = WriterCSV(filename=dir_name + '/filter.csv',
                               first_row=first_row)
        write_res = {
            'ok': csv_ok,
            'filter': csv_filter
        }
        """
        Creating work threads
        """
        mythreads = CreateThreads(config, tasks,
                                  write_res=write_res, cls=MyTask)
        while mythreads.is_threads() and not os.path.isfile('stop'):
            sleep(1)
        mythreads.finish()
        print("Process terminated!")
