from concurrent import futures
import grpc
import time
import re
import threading
from cachetools import TTLCache
import logging
from common.database import SessionLocal, engine
from common import models
import service_pb2
import service_pb2_grpc

# Import da prometheus_client
import prometheus_client
from prometheus_client import Counter, Gauge, start_http_server
import socket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

HOSTNAME = socket.gethostname()

SERVICE_LABEL_COMMAND = "grpc_command"
SERVICE_LABEL_QUERY   = "grpc_query"

GRPC_COMMAND_REQUESTS = Counter(
    'grpc_command_requests_total',
    'Numero di richieste gRPC di tipo Command',
    ['service', 'node']
)
GRPC_COMMAND_LATENCY = Gauge(
    'grpc_command_latency_ms',
    'Latency di richieste gRPC Command (ms)',
    ['service', 'node']
)

GRPC_QUERY_REQUESTS = Counter(
    'grpc_query_requests_total',
    'Numero di richieste gRPC di tipo Query',
    ['service', 'node']
)
GRPC_QUERY_LATENCY = Gauge(
    'grpc_query_latency_ms',
    'Latency di richieste gRPC Query (ms)',
    ['service', 'node']
)


class UserCommandServiceServicer(service_pb2_grpc.UserCommandServiceServicer):
    def __init__(self):
        self.request_cache = TTLCache(maxsize=10000, ttl=600)
        self.cache_lock = threading.Lock()

    def is_valid_email(self, email):
        regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(regex, email) is not None

    def RegisterUser(self, request, context):
        start_t = time.time()

        GRPC_COMMAND_REQUESTS.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).inc()

        if not request.request_id:
            context.set_details("Manca request_id")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
            return service_pb2.RegisterUserResponse()

        with self.cache_lock:
            if request.request_id in self.request_cache:
                logger.info(f"Richiesta duplicata: {request.request_id}")
                message = self.request_cache[request.request_id]
                
                elapsed_ms = (time.time() - start_t)*1000
                GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
                return service_pb2.RegisterUserResponse(message=message)

        if not self.is_valid_email(request.email):
            message = "Formato email non valido."
            with self.cache_lock:
                self.request_cache[request.request_id] = message
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
            return service_pb2.RegisterUserResponse(message=message)

        hv = request.high_value if request.high_value != 0.0 else None
        lv = request.low_value if request.low_value != 0.0 else None

        if hv is not None and lv is not None:
            if hv <= lv:
                message = "high_value deve essere maggiore di low_value."
                with self.cache_lock:
                    self.request_cache[request.request_id] = message
                elapsed_ms = (time.time() - start_t)*1000
                GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
                return service_pb2.RegisterUserResponse(message=message)

        session = SessionLocal()
        try:
            existing_user = session.query(models.User).filter_by(email=request.email).first()
            if existing_user:
                message = "L'utente è già registrato!"
            else:
                new_user = models.User(
                    email=request.email, 
                    ticker=request.ticker, 
                    high_value=hv, 
                    low_value=lv
                )
                session.add(new_user)
                session.commit()
                message = "Registrazione avvenuta con successo!"

            with self.cache_lock:
                self.request_cache[request.request_id] = message

            return service_pb2.RegisterUserResponse(message=message)
        except Exception as e:
            session.rollback()
            logger.error(f"Errore nella registrazione: {e}")
            context.set_details(f'Error: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.RegisterUserResponse()
        finally:
            session.close()
            
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)

    def UpdateUser(self, request, context):
        start_t = time.time()
        GRPC_COMMAND_REQUESTS.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).inc()

        if not request.request_id:
            context.set_details("Manca request_id")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
            return service_pb2.UpdateUserResponse()

        with self.cache_lock:
            if request.request_id in self.request_cache:
                message = self.request_cache[request.request_id]
                elapsed_ms = (time.time() - start_t)*1000
                GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
                return service_pb2.UpdateUserResponse(message=message)

        if not self.is_valid_email(request.email):
            message = "Formato email non valido."
            with self.cache_lock:
                self.request_cache[request.request_id] = message
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
            return service_pb2.UpdateUserResponse(message=message)

        hv = request.high_value if request.high_value != 0.0 else None
        lv = request.low_value if request.low_value != 0.0 else None

        if hv is not None and lv is not None:
            if hv <= lv:
                message = "high_value deve essere maggiore di low_value: RIPROVARE"
                with self.cache_lock:
                    self.request_cache[request.request_id] = message
                elapsed_ms = (time.time() - start_t)*1000
                GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
                return service_pb2.UpdateUserResponse(message=message)

        session = SessionLocal()
        try:
            user = session.query(models.User).filter_by(email=request.email).first()
            if user:
                updated = False
                if user.ticker != request.ticker:
                    user.ticker = request.ticker
                    user.high_value = None
                    user.low_value = None
                    user.high_notification_sent = False
                    user.low_notification_sent = False
                    updated = True

                if request.high_value != 0.0 and request.high_value != user.high_value:
                    user.high_value = request.high_value
                    user.high_notification_sent = False
                    updated = True

                if request.low_value != 0.0 and request.low_value != user.low_value:
                    user.low_value = request.low_value
                    user.low_notification_sent = False
                    updated = True

                if updated:
                    session.commit()
                    message = "Utente aggiornato correttamente!"
                else:
                    message = "Nessuna modifica effettuata."
            else:
                message = "Utente non trovato."

            with self.cache_lock:
                self.request_cache[request.request_id] = message
            return service_pb2.UpdateUserResponse(message=message)
        except Exception as e:
            session.rollback()
            logger.error(f"Errore aggiornamento utente: {e}")
            context.set_details(f'Errore: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.UpdateUserResponse()
        finally:
            session.close()
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)

    def DeleteUser(self, request, context):
        start_t = time.time()
        GRPC_COMMAND_REQUESTS.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).inc()

        if not request.request_id:
            context.set_details("Manca request_id")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
            return service_pb2.DeleteUserResponse()

        with self.cache_lock:
            if request.request_id in self.request_cache:
                message = self.request_cache[request.request_id]
                elapsed_ms = (time.time() - start_t)*1000
                GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
                return service_pb2.DeleteUserResponse(message=message)

        if not self.is_valid_email(request.email):
            message = "Formato email non valido."
            with self.cache_lock:
                self.request_cache[request.request_id] = message
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
            return service_pb2.DeleteUserResponse(message=message)

        session = SessionLocal()
        try:
            user = session.query(models.User).filter_by(email=request.email).first()
            if user:
                session.delete(user)
                session.commit()
                message = "Utente cancellato correttamente"
            else:
                message = "Utente non trovato"

            with self.cache_lock:
                self.request_cache[request.request_id] = message
            return service_pb2.DeleteUserResponse(message=message)
        except Exception as e:
            session.rollback()
            logger.error(f"Errore nella cancellazione utente: {e}")
            context.set_details(f'Error: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.DeleteUserResponse()
        finally:
            session.close()
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)

    def LoginUser(self, request, context):
        start_t = time.time()
        GRPC_COMMAND_REQUESTS.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).inc()

        if not self.is_valid_email(request.email):
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)
            return service_pb2.LoginUserResponse(message="Formato email non valido.", success=False)

        session = SessionLocal()
        try:
            user = session.query(models.User).filter_by(email=request.email).first()
            if user:
                message = "Login avvenuto con successo!"
                success = True
            else:
                message = "Utente non trovato!"
                success = False
            return service_pb2.LoginUserResponse(message=message, success=success)
        except Exception as e:
            logger.error(f"Errore login: {e}")
            context.set_details(f'Errore: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.LoginUserResponse(message="Internal error.", success=False)
        finally:
            session.close()
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_COMMAND_LATENCY.labels(service=SERVICE_LABEL_COMMAND, node=HOSTNAME).set(elapsed_ms)



class UserQueryServiceServicer(service_pb2_grpc.UserQueryServiceServicer):
    def __init__(self):
        pass

    def GetLatestValue(self, request, context):
        start_t = time.time()
        GRPC_QUERY_REQUESTS.labels(service=SERVICE_LABEL_QUERY, node=HOSTNAME).inc()

        session = SessionLocal()
        try:
            user = session.query(models.User).filter_by(email=request.email).first()
            if not user:
               
                return service_pb2.GetLatestValueResponse(
                    email=request.email,
                    ticker="",
                    value=0.0,
                    timestamp=""
                )
            ticker = user.ticker
            latest_data = session.query(models.FinancialData)\
                .filter_by(ticker=ticker)\
                .order_by(models.FinancialData.timestamp.desc())\
                .first()
            if latest_data:
                return service_pb2.GetLatestValueResponse(
                    email=request.email,
                    ticker=latest_data.ticker,
                    value=latest_data.value,
                    timestamp=latest_data.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                context.set_details(f"Nessun dato disponibile per il ticker: {ticker}")
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return service_pb2.GetLatestValueResponse()
        except Exception as e:
            logger.error(f"Errore nel recupero ultimo valore: {e}")
            context.set_details(f'Errore: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.GetLatestValueResponse()
        finally:
            session.close()
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_QUERY_LATENCY.labels(service=SERVICE_LABEL_QUERY, node=HOSTNAME).set(elapsed_ms)

    def GetAverageValue(self, request, context):
        start_t = time.time()
        GRPC_QUERY_REQUESTS.labels(service=SERVICE_LABEL_QUERY, node=HOSTNAME).inc()

        session = SessionLocal()
        try:
            user = session.query(models.User).filter_by(email=request.email).first()
            if not user:
                context.set_details("Utente non trovato.")
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return service_pb2.GetAverageValueResponse()

            ticker = user.ticker
            data = session.query(models.FinancialData)\
                .filter_by(ticker=ticker)\
                .order_by(models.FinancialData.timestamp.desc())\
                .limit(request.count)\
                .all()

            if data and len(data) > 0:
                average_value = sum(entry.value for entry in data) / len(data)
                return service_pb2.GetAverageValueResponse(
                    email=request.email,
                    ticker=ticker,
                    average_value=average_value
                )
            else:
                context.set_details(f"Nessun valore disponibile per il ticker: {ticker}")
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return service_pb2.GetAverageValueResponse()
        except Exception as e:
            logger.error(f"Errore nel calcolo media: {e}")
            context.set_details(f'Errore: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.GetAverageValueResponse()
        finally:
            session.close()
            elapsed_ms = (time.time() - start_t)*1000
            GRPC_QUERY_LATENCY.labels(service=SERVICE_LABEL_QUERY, node=HOSTNAME).set(elapsed_ms)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service_pb2_grpc.add_UserCommandServiceServicer_to_server(UserCommandServiceServicer(), server)
    service_pb2_grpc.add_UserQueryServiceServicer_to_server(UserQueryServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    logger.info("gRPC Server in ascolto sulla porta 50051...")

    from prometheus_client import start_http_server
    start_http_server(8000)  
    logger.info("Prometheus metrics esposte su porta 8000 (/metrics).")

    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)
        logger.info("Server gRPC fermato")


if __name__ == '__main__':
    serve()
