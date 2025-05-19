from kafka import KafkaConsumer
# import pytz


def consumer():
    cs = KafkaConsumer(
        bootstrap_servers=['47.128.81.230:8003'],
        auto_offset_reset='latest')
    cs.subscribe(['dannv'])
    for message in cs:
        print(message)


consumer()