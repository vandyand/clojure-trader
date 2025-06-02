SELECT
  instrument,
  time,
  open,
  high,
  low,
  close,
  volume
FROM
  aligned_candles
WHERE
  instrument = 'EUR_USD'
ORDER BY
  time DESC
LIMIT 12;
