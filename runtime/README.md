# Runtime

The first runtime slice includes:

- guarded state transitions through the vehicle workflow;
- a tool executor with timing, transient retries, and side-effect events;
- scoped confirmation tokens for reservation and navigation;
- a thread-safe Trace Schema v0.1.0 JSONL writer.

It coordinates components without absorbing their domain logic. See the
[in-car restaurant agent](../examples/in_car_restaurant_agent/) for an
end-to-end execution.
