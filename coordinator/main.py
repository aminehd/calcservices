"""Coordinator: holds weights, waits for all workers, averages, bumps the step."""
# TODO: GET  /weights        -> current weights + step
# TODO: POST /report         -> record a worker's grad; when all N are in, average and advance
