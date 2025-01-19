import time

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_time=60):
        self.failure_threshold = failure_threshold
        self.failure_count = 0
        self.last_failure_time = 0
        self.recovery_time = recovery_time
        self.state = 'CLOSED'

    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_time:
               
                self.state = 'HALF-OPEN'
                print("Circuito in stato HALF-OPEN: sto tentando di ripristinare il servizio...")
            else:
                print("Circuito in stato OPEN: le richieste sono attualmente bloccate.")
                raise Exception("Circuit is open")

        try:
            result = func(*args, **kwargs)
         
            self.failure_count = 0
            self.state = 'CLOSED'
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            print(f"Errore durante la chiamata a '{func.__name__}': {e}. Numero di fallimenti: {self.failure_count}/{self.failure_threshold}")

            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                print("Circuito aperto: il numero massimo di fallimenti è stato raggiunto. Bloccando le chiamate per un po'.")
            raise e

