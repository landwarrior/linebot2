def log(logger):

    def log_wrapper(func):

        def wrapper(*args, **kwargs):
            logger.info(f"--START-- {func.__name__}")
            res = func(*args, **kwargs)
            logger.debug(f"res: {res}")
            logger.info(f"-- END -- {func.__name__}")
            return res

        wrapper.__doc__ = func.__doc__

        return wrapper

    return log_wrapper
