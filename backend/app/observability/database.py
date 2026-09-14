import time
from sqlalchemy import event
from app.observability.metrics import DB_TIME, DB_ERRORS


def instrument_engine(engine, database):
    @event.listens_for(engine, 'before_cursor_execute')
    def before(conn, cursor, statement, parameters, context, executemany):
        context._eco_started = time.monotonic()

    @event.listens_for(engine, 'after_cursor_execute')
    def after(conn, cursor, statement, parameters, context, executemany):
        DB_TIME.labels(database).observe(time.monotonic() - context._eco_started)

    @event.listens_for(engine, 'handle_error')
    def failed(context):
        DB_ERRORS.labels(database).inc()
        started = getattr(context.execution_context, '_eco_started', None)
        if started is not None:
            DB_TIME.labels(database).observe(time.monotonic() - started)
