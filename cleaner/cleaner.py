import time
from sqlalchemy.orm import sessionmaker
from common.models import FinancialData
from sqlalchemy.exc import OperationalError
from common.database import SessionLocal


def remove_outdated_entries():
    with SessionLocal() as db_session:
        ticker_list = db_session.query(FinancialData.ticker).distinct().all()
        unique_tickers = [t[0] for t in ticker_list]

        for current_ticker in unique_tickers:
            count_records = db_session.query(FinancialData).filter_by(ticker=current_ticker).count()

            if count_records > 20:
                excess_records = count_records - 20

                obsolete_records = (
                    db_session.query(FinancialData.id)
                    .filter_by(ticker=current_ticker)
                    .order_by(FinancialData.timestamp.asc())
                    .limit(excess_records)
                    .all()
                )

                ids_to_delete = [record.id for record in obsolete_records]

                db_session.query(FinancialData).filter(FinancialData.id.in_(ids_to_delete)).delete(synchronize_session=False)

                db_session.commit()
                print(f"Rimossi {excess_records} record obsoleti per il ticker {current_ticker}")
            else:
                print(f"Nessun record da eliminare per il ticker {current_ticker}")


if __name__ == '__main__':
    while True:
        print("Avvio processo di pulizia dei dati...")
        remove_outdated_entries()
        print("Pulizia completata. Il processo andrÃ  in pausa per 24 ore.")

        time.sleep(86400)