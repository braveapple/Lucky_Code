from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import ast
import time
import Queue
import threading
import argparse
import requests
import numpy as np
from tqdm import tqdm

class Downloader(object):
  def __init__(self, input_file, output_dir, use_proxy):
    super(Downloader, self).__init__()
    self.output_dir = output_dir
    self.use_proxy = use_proxy
    self.input_queue = Queue.Queue()
    self.output_queue = Queue.Queue()
    input_array = np.loadtxt(args.input_file, dtype='|S200', delimiter=',', skiprows=1)
    self.image_num = input_array.shape[0]
    for line in input_array:
      self.input_queue.put(line)
    self.headers =  {
      'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
    }

    self.proxies = {
      'https':'socks5://127.0.0.1:1080', 
      'http':'socks5://127.0.0.1:1080'
    }

  def worker(self):
    while True:
      try:
        person_name, person_index, image_file, bbox, height_width, url = self.input_queue.get_nowait()
      except Exception:
        break
      image_file = os.path.join(self.output_dir, '{}_{}'.format(person_name, person_index), image_file)
      try:
        if self.use_proxy:
          response = requests.get(url, headers=self.headers, proxies=self.proxies)
        else:
          response = requests.get(url, headers=self.headers)
        response.raise_for_status()
      except Exception:
        self.output_queue.put('{},{},{}\n'.format(os.path.relpath(image_file, self.output_dir), bbox, height_width))
        continue
      image_root = os.path.dirname(image_file)
      if not os.path.exists(image_root):
        try:
          os.makedirs(image_root)
        except OSError:
          pass
      with open(image_file, 'wb') as f_image:
        f_image.write(response.content)
      self.output_queue.put('{},{},{}\n'.format(os.path.relpath(image_file, self.output_dir), bbox, height_width))

  def logger(self):
    bbox_file = os.path.join(self.output_dir, 'bbox.txt')
    with open(bbox_file, 'w') as f:
      for line_idx in tqdm(range(self.image_num)):
        line = self.output_queue.get()
        f.write(line)

  def start_worker(self, worker_num):
    self.workers = []
    for worker_idx in range(worker_num):
      worker_func = threading.Thread(target=self.worker, args=())
      worker_func.setDaemon(True)
      worker_func.start()
      self.workers.append(worker_func)
    
    logger_func = threading.Thread(target=self.logger, args=())
    logger_func.setDaemon(True)
    logger_func.start()
    self.workers.append(logger_func)

    try:
      while self.any_alive():
        time.sleep(100)
        pass
    except KeyboardInterrupt:
      print('Stopped by keyboard') 

  def any_alive(self):
    alive = False
    for worker in self.workers:
      if worker.isAlive():
        alive = True
        break
    return alive

def parse_args():
  description = "Download images"
  
  parser = argparse.ArgumentParser(description=description)
  parser.add_argument('--input_file', type=str, help='The path of the input file')
  parser.add_argument('--output_dir', type=str, help='The path of the output directory')
  parser.add_argument('--worker_num', type=int, default=4, help='The number of works')
  parser.add_argument('--use_proxy', type=ast.literal_eval, default=False, help='Wether to use proxies')

  args = parser.parse_args()
  return args

if __name__ == '__main__':

  args = parse_args()
  assert os.path.exists(args.input_file), 'Not found the file => {}'.format(args.input_file)
  if not os.path.exists(args.output_dir):
    os.makedirs(args.output_dir)
  downloader = Downloader(args.input_file, args.output_dir, args.use_proxy)
  print('Start!')
  downloader.start_worker(worker_num=args.worker_num)
