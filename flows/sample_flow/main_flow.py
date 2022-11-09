from prefect import flow, get_run_logger


@flow
def say_hello(name: str) -> str:
    get_run_logger().info(f"Hello {name}")
