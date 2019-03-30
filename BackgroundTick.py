import nidaqmx
from ctypes import c_bool
from background_helper import Task_Proxy
from time import sleep

class BackgroundTick(Task_Proxy):

    def __init__(self, name, args=(), kwargs={}):
	
        super().logger.info('Starting PyTick background thread')
	self._should_terminate_flag = mp.Value(c_bool, 0)
	
        pipe_parent, pipe_child = mp.Pipe(True)
        wrapper_args = super()._prepare_wrapper_args(
            pipe_child, self._should_terminate_flag
        )
        wrapper_args.extend(args)
        self.process = mp.Process(
            target=self._wrapper, name=name, args=wrapper_args, kwargs=kwargs
        )
        self.process.daemon = True
        self.process.start()
        self.pipe = pipe_parent
	
        niTask = nidaqmx.Task()
	niTask.ao_channels.add_ao_voltage_chan('Dev1/ao1')
	self.niTask = niTask

    def _wrapper(self, pipe, _should_terminate_flag, *args, **kwargs):
        while True:
            if pipe.poll(0):
                recvStr = pipe.recv()
                if recvStr == 'trigger':
                    try:
                        self.trigger(**kwargs)
                    except Exception as e:
                        pipe.send(e)
                        if not isinstance(e, EarlyCancellationError):
                            import traceback
                            super().logger.info(traceback.format_exc())
                        break
                
                elif recvStr == 'stopped':
                    break
                else:
                    super().logger.info('Invalid trigger received')
        
        pipe.close()
        super().logger.debug("Exiting _wrapper")

    def fetch(self):
        print('En Taro Tassadar!')

    def trigger(self, skipFirst=0, skipFactor=1):
        for _ in range(skipFirst + skipFactor + 1):
            self.niTask.write([3.3], auto_start=True)
            sleep(0.002)
            self.niTask.write([0.0], auto_start=True)
	    sleep(0.001)

    def finish(self, timeout=1):
        self.niTask.stop()
        if self.process is not None:
            self.process.join(timeout)
            self.process = None
