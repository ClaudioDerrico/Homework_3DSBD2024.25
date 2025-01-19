import smtplib
from email.mime.text import MIMEText

def send_email(to_email, ticker, threshold_value, ChoosenThreshold ,value_ticker_registered):
    subject = f"Notifica Ticker {ticker}"
    if(ChoosenThreshold=="HIGH"):
        body = f"Il valore del ticker {ticker} registrato ({value_ticker_registered}) ha superato la soglia {ChoosenThreshold}: {threshold_value}"
    else:
        body = f"Il valore del ticker {ticker} registrato ({value_ticker_registered}) è ora inferiore alla soglia {ChoosenThreshold}: {threshold_value}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = "progettiunict@gmail.com"
    msg['To'] = to_email

    
    with smtplib.SMTP('smtp.gmail.com', 587) as s:
        s.starttls()
        s.login("progettiunict@gmail.com", "sznamzimewelchvq")
        s.send_message(msg)
    print(f"Email inviata a {to_email} per ticker {ticker}, soglia {ChoosenThreshold}")