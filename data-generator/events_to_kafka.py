import click
import time
import json
import random
import os
import uuid
from dotenv import load_dotenv

from datetime import datetime, timedelta
from confluent_kafka import Producer
import socket

load_dotenv()
username = os.environ.get('SASL_PLAIN_USERNAME')
password = os.environ.get('SASL_PLAIN_PASSWORD')
bootstrap_servers = os.environ.get('BOOTSTRAP_SERVERS')

if not username or not password or not bootstrap_servers:
    raise EnvironmentError('Missing required environment variables in the .env file or the file is empty.')


@click.command()
@click.option('--topic', help='the kafka topic. bookings_topic by default', default='bookings_topic')
@click.option('--sample', type=int, default=10_000)
@click.option('--sleep', type=float, default=1)
@click.option('--mps', help='number of messages per sleep (by default 200, and as by default sleep is 1, 200 messages/s', type=int, default=200)
@click.option('--repeat', type=int, default=1)
@click.option('--bootstrap-servers', default=bootstrap_servers)
@click.option('--security_protocol', default='SASL_SSL')
@click.option('--sasl_mechanism', default='PLAIN')
@click.option('--sasl_plain_username', default=username)
@click.option('--sasl_plain_password', default=password)
@click.option('--utc', help='UTC datetime for tmstmp by default', type=bool, default=True)
def produce(topic,
            sample,
            sleep,
            mps,
            repeat,
            bootstrap_servers,
            security_protocol,
            sasl_mechanism,
            sasl_plain_username,
            sasl_plain_password,
            utc):

    conf = {
        'bootstrap.servers': bootstrap_servers,
        'client.id': socket.gethostname(),
        'security.protocol': security_protocol,
        'sasl.mechanism': sasl_mechanism,
        'sasl.username': sasl_plain_username,
        'sasl.password': sasl_plain_password,
        'compression.type': 'lz4'
    }

    producer = Producer(conf)

    onqueue = -1
    t = time.time()
    for _ in range(repeat):

        event_types = random.choices(["booking","search","cancellation","refund"], weights=[25,60,10,5], k=sample)
        devices = random.choices(["desktop","mobile","tablet","smart_tv","smartwatch"], weights=[30,55,5,5,5], k=sample)
        browsers = random.choices(["Chrome","Brave","Firefox","Safari"], weights=[65,5,10,20], k=sample)
        oss = random.choices(["Windows", "Mac OS", "Linux"], weights=[7,2,1], k=sample)
        user_ids = random.choices([123456,234567,345678,456789,567890,678901,789012,890123,901234,101234,112345,123456,134567,145678,156789,167890,178901,189012,190123,201234], k=sample)
        user_locations = random.choices(["Spain","Portugal","Italy"], weights=[6,3,1], k=sample)
        start_datetimes = [datetime.utcnow() + timedelta(days=random.randint(3,67), seconds=random.randint(0,3600*24)) for _ in range(sample)]
        currencies = random.choices(["USD","EUR","GBP","JPY","CNY"], weights=[40,30,10,10,10], k=sample)
        card_ids = random.choices([123456,234567,345678,456789,567890,678901,789012,890123,901234], k=sample)
        card_issuers = random.choices(["Visa","Mastercard","American Express","Discover"], weights=[40,30,20,10], k=sample)

        for i in range(sample):
            message = {
                'event_time': datetime.strftime(datetime.utcnow() if utc else datetime.now(), '%Y-%m-%d %H:%M:%S'),
                'event_id': str(uuid.uuid4()),
                'event_type': event_types[i],
                'device': devices[i],
                'browser': browsers[i],
                'os': oss[i],
                'product_id' : random.randint(3278123,3378123),
                'user_id': user_ids[i],
                'user_location': user_locations[i],
                'start_datetime': datetime.strftime(start_datetimes[i],'%Y-%m-%d %H:%M:%S'),
                'end_datetime': datetime.strftime(start_datetimes[i] + timedelta(days=random.randint(1,20)),'%Y-%m-%d %H:%M:%S'),
                'price': int(max(random.gauss(mu=750, sigma=90),20)),
                'currency': currencies[i],
                'card_id': card_ids[i],
                'card_issuer': card_issuers[i],
            }

            msg = json.dumps(message).encode('utf-8')

            # print(message)
            producer.produce(topic, value=msg)

            onqueue += 1
            while onqueue >= mps:
                before_onqueue = onqueue
                time.sleep(sleep)
                onqueue = producer.flush(2)
                sent = before_onqueue - onqueue
                dt = time.time() - t
                print(
                    f"Uploading rate: {int(sent/dt)} messages/second. {i} of {sample}")
                t = time.time()

        if sleep:
            producer.flush()
            time.sleep(sleep)
            print(f'{sample} sent! {_+1} of {repeat} - {datetime.now()}')
        producer.flush()


if __name__ == '__main__':
    produce()