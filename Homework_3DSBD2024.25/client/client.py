import grpc
import service_pb2
import service_pb2_grpc
import yfinance as yf
import datetime
import random
import string
from time import sleep
import logging

session_email = None

def generate_request_id():
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S%f')
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return f"{timestamp}_{random_str}"

def ticker_verifier(ticker):
    logging.getLogger('yfinance').setLevel(logging.CRITICAL)
    try:
        dati = yf.download(ticker, period="1d", progress=False)
        if not dati.empty:
            print(f"Il ticker '{ticker}' è valido.")
            return True
        else:
            print(f"Il ticker '{ticker}' non è valido o non è possibile scaricare i dati.")
            return False
    except Exception as e:
        print(f"Errore durante la verifica del ticker: {e}")
        return False

def send_request_with_retry(stub_method, request, max_retries=5, channel=None, stub=None):
    attempts = 0
    while attempts < max_retries:
        try:
            response = stub_method(request, timeout=10)
            return response
        except grpc.RpcError as e:
            if e.code() in [grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.UNAVAILABLE]:
                attempts += 1
                print(f"Tentativo {attempts} di {max_retries} fallito. Connessione al server non riuscita. Riprovo...")

                if channel and channel.get_state(True) in [grpc.ChannelConnectivity.TRANSIENT_FAILURE, grpc.ChannelConnectivity.SHUTDOWN]:
                    print("Il canale è in errore. Sto tentando di ripristinare la connessione...")
                    channel = grpc.insecure_channel('localhost:50051')
                    
                sleep(10)
                continue
            else:
                print("Errore durante la comunicazione con il server. Riprova più tardi.")
                break
    print("Impossibile contattare il server dopo diversi tentativi.")
    return None

def run():
    global session_email
    with grpc.insecure_channel('localhost:50051') as canale:
        
        command_stub = service_pb2_grpc.UserCommandServiceStub(canale)
        read_stub = service_pb2_grpc.UserQueryServiceStub(canale)

        while True:
            print("\n--- Menù di avvio ---")
            print("1. Login")
            print("2. Registrazione")
            print("3. Esci")
            scelta = input("Inserisci il numero dell'operazione desiderata: ")

            if scelta == '1':
                email = input("Inserisci la tua email: ")
                request = service_pb2.LoginUserRequest(email=email)
                response = send_request_with_retry(command_stub.LoginUser, request)
                if response and response.success:
                    print(response.message)
                    session_email = email
                    user_session(command_stub, read_stub)
                elif response:
                    print(response.message)
                else:
                    print("Errore durante il login.")
            elif scelta == '2':
                email = input("Inserisci l'email dell'utente: ")
                ticker = input("Inserisci il ticker di interesse: ")
                hv_input = input("Vuoi impostare un valore high_value? (s/n): ")
                high_value = None
                if hv_input.lower() == 's':
                    try:
                        high_value = float(input("Inserisci high_value: "))
                    except ValueError:
                        print("Valore non valido, ignorato.")

                lv_input = input("Vuoi impostare un valore low_value? (s/n): ")
                low_value = None
                if lv_input.lower() == 's':
                    try:
                        low_value = float(input("Inserisci low_value: "))
                    except ValueError:
                        print("Valore non valido, ignorato.")

                if ticker_verifier(ticker):
                    request_id = generate_request_id()
                    req = service_pb2.RegisterUserRequest(email=email, ticker=ticker, request_id=request_id)
                    if high_value is not None:
                        req.high_value = high_value
                    if low_value is not None:
                        req.low_value = low_value

                    response = send_request_with_retry(command_stub.RegisterUser, req)
                    if response:
                        print(response.message)
                        if "success" in response.message.lower():
                            session_email = email
                            user_session(command_stub, read_stub)
                    else:
                        print("Errore durante la registrazione.")
                else:
                    print("Ticker non valido. Registrazione annullata.")
            elif scelta == '3':
                print("Uscita dal programma... Alla prossima!")
                break
            else:
                print("Scelta non valida. Riprova.")


def user_session(command_stub, read_stub):
    global session_email
    while True:
        print(f"\n--- BENVENUTO {session_email} ---")
        print("\nSeleziona un'operazione:")
        print("1. Aggiornamento Ticker/Soglie")
        print("2. Cancellazione Account")
        print("3. Recupero dell'ultimo valore disponibile")
        print("4. Calcolo della media degli ultimi X valori")
        print("5. Logout")
        scelta = input("Inserisci il numero dell'operazione desiderata: ")

        if scelta == '1':
            ticker = input("Inserisci il nuovo ticker: ")
            hv_input = input("Vuoi inserire un high_value? (s/n): ")
            high_value = None
            if hv_input.lower() == 's':
                try:
                    high_value = float(input("Inserisci high_value: "))
                except ValueError:
                    print("Valore non valido, ignorato.")
            lv_input = input("Vuoi inserire un low_value? (s/n): ")
            low_value = None
            if lv_input.lower() == 's':
                try:
                    low_value = float(input("Inserisci low_value: "))
                except ValueError:
                    print("Valore non valido, ignorato.")

            if ticker_verifier(ticker):
                request_id = generate_request_id()
                req = service_pb2.UpdateUserRequest(email=session_email, ticker=ticker, request_id=request_id)
                if high_value is not None:
                    req.high_value = high_value
                if low_value is not None:
                    req.low_value = low_value

                response = send_request_with_retry(command_stub.UpdateUser, req)
                if response:
                    print(response.message)
                else:
                    print("Errore durante l'aggiornamento.")
            else:
                print("Ticker non valido. Aggiornamento annullato.")
        elif scelta == '2':
            request_id = generate_request_id()
            request = service_pb2.DeleteUserRequest(email=session_email, request_id=request_id)
            response = send_request_with_retry(command_stub.DeleteUser, request)
            if response:
                print(response.message)
                if "cancellato" in response.message.lower():
                    session_email = None
                    print("Sei stato disconnesso.")
                    break
            else:
                print("Errore durante la cancellazione dell'account.")
        elif scelta == '3':
            request = service_pb2.GetLatestValueRequest(email=session_email)
            try:
                response = read_stub.GetLatestValue(request, timeout=5)
                if response.ticker:
                    print(f"Ultimo valore per {response.ticker}: {response.value} (Timestamp: {response.timestamp})")
                else:
                    print("Nessun dato disponibile.")
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.NOT_FOUND:
                    print("Nessun valore disponibile. Il data collector potrebbe non essere aggiornato.")
                else:
                    print(f"Errore durante il recupero dell'ultimo valore: {e.details()}")
        elif scelta == '4':
            try:
                count = int(input("Quanti valori vuoi considerare per la media? "))
                request = service_pb2.GetAverageValueRequest(email=session_email, count=count)
                try:
                    response = read_stub.GetAverageValue(request, timeout=5)
                    if response and response.ticker:
                        print(f"Valore medio per {response.ticker}: {response.average_value}")
                    elif response:
                        print("Nessun dato disponibile per l'utente specificato.")
                except grpc.RpcError as e:
                    if e.code() == grpc.StatusCode.NOT_FOUND:
                        print("Nessun valore disponibile. Il data collector potrebbe non essere aggiornato.")
                    else:
                        print(f"Errore durante il calcolo della media: {e.details()}")
            except ValueError:
                print("Per favore, inserisci un numero intero valido.")
        elif scelta == '5':
            print("Logout effettuato.")
            session_email = None
            break
        else:
            print("Scelta non valida. Riprova.")

if __name__ == '__main__':
    run()
