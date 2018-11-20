import time
from functools import wraps

def timeThis(func):
    '''
    Decorator that reports the execution time.
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print '\n- = t i m e T h i s = -'
        print 'Function: {}\nargs:{}\nkwargs:{}\nExecution time: {} sec'.format(func.__name__, args, kwargs, end-start)
        print '- = t i m e T h i s = -\n\n\n'
        return result
    return wrapper
