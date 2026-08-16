# Tools

The minimal registry exposes six sandbox tools:

- `get_current_location`
- `search_restaurants`
- `get_route`
- `check_reservation_availability`
- `create_reservation`
- `start_navigation`

The last two are declared as side-effecting tools. They require a matching
confirmation token, emit explicit side-effect events, and use an idempotency
key to prevent duplicate reservations after an uncertain timeout.
