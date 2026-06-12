import time

class RateLimiter:
    def __init__(self, rpm_limit=None, tpm_limit=None):
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.history = []  # list of tuples: (timestamp, token_count)

    def wait_if_needed(self, estimated_tokens):
        if not self.rpm_limit and not self.tpm_limit:
            return

        while True:
            now = time.time()
            # Remove entries older than 60 seconds
            self.history = [entry for entry in self.history if now - entry[0] < 60]

            # Calculate current usage in the window
            current_rpm = len(self.history)
            current_tpm = sum(entry[1] for entry in self.history)

            # Check limits
            rpm_exceeded = self.rpm_limit and current_rpm >= self.rpm_limit
            tpm_exceeded = self.tpm_limit and (current_tpm + estimated_tokens) > self.tpm_limit

            if not rpm_exceeded and not tpm_exceeded:
                break

            # Calculate wait time: wait until the oldest transaction slips out of the 60-second window
            if self.history:
                oldest_time = self.history[0][0]
                sleep_time = 60 - (now - oldest_time) + 0.1
                if sleep_time > 0:
                    time.sleep(sleep_time)
            else:
                # Safety fallback sleep
                time.sleep(1)

    def record_request(self, token_count):
        self.history.append((time.time(), token_count))
