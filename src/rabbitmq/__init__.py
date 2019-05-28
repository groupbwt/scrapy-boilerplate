import os, sys

from .BaseConsumer import BaseConsumer
from .BaseProducer import BaseProducer
from .PikaFactory import PikaFactory
from .RabbitConnection import RabbitConnection


cur_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.abspath(os.path.join(cur_dir, '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)
