class BookingConflictError(Exception):
  """Raised when an LSA is already booked for the requested time."""