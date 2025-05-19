from kafka import KafkaProducer


def init_kafka_producer(bootstrap_server: str) -> KafkaProducer:
    return KafkaProducer(bootstrap_servers=[bootstrap_server],
                         request_timeout_ms=5000,
                         max_block_ms=5000)
