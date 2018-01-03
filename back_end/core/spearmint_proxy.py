from sys import path
import os
from conf import settings

# TEST
path.insert(0, os.path.realpath(settings.SPEARMINT))
spearmint_lite = __import__('spearmint-lite')
globals().update(vars(spearmint_lite))
