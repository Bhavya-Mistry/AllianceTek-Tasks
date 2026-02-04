# Room

1. room_id (string uuid)
2. status (waiting/active/finished)
3. created_at (timestamp)
4. time_limit_sec (int)
5. problem_id (string)
6. players (list of Player objects, max 2)


# Player

1. player_id (string, from socket sesion id OR generated uuid)
2. username (string)
3. joined_at (timestamp)
4. submitted (bool, default false)