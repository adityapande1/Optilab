# Metrics
Documentation for the `metrics` used in the project.


---
## Metric : Profit and Loss `pnl`

## 1. pnl of `df_position`
- Each leg (call/put) has a `df_position` with its index as the timestamps over which position was open. 
- The `pnl` is calculated based by the function : `backtest.metrics.update_metric_pnl(**kwargs)`
- `per_lot_transaction_cost` X `num_lots` (>0) is deducted at the  start(open) and end(close) of timestamp 
### Example
```python
# Sample starting df_position for a leg : df_position

                        price
timestamp                      
2024-01-09 09:15:00     85.00
2024-01-09 09:16:00     75.00
2024-01-09 09:17:00     70.00
2024-01-09 09:18:00     75.00
2024-01-09 09:19:00     95.00
2024-01-09 09:20:00    105.00
2024-01-09 09:21:00    110.00
2024-01-09 09:22:00    112.00
2024-01-09 09:23:00    113.00
2024-01-09 09:24:00    115.00
2024-01-09 09:25:00    105.00
2024-01-09 09:26:00    102.00
2024-01-09 09:27:00    100.00
2024-01-09 09:28:00    101.50
2024-01-09 09:29:00    102.50
2024-01-09 09:30:00    100.00

# Update the pnl
from backtest.metrics import update_metric_pnl
update_metric_pnl(df = df_position, 
                  trade_type = 'long', 
                  per_lot_transaction_cost = 50, 
                  lot_size = 75, 
                  num_lots = 1)

# After applying the update function, the df_position is updated as below

                        price  gross_step_pnl  transaction_cost  net_step_pnl     pnl
timestamp                                                                         
2024-01-09 09:15:00      85.0         NaN             50.0           -50.0       -50.0
2024-01-09 09:16:00      75.0      -750.0              0.0          -750.0      -800.0
2024-01-09 09:17:00      70.0      -375.0              0.0          -375.0     -1175.0
2024-01-09 09:18:00      75.0       375.0              0.0           375.0      -800.0
2024-01-09 09:19:00      95.0      1500.0              0.0          1500.0       700.0
2024-01-09 09:20:00     105.0       750.0              0.0           750.0      1450.0
2024-01-09 09:21:00     110.0       375.0              0.0           375.0      1825.0
2024-01-09 09:22:00     112.0       150.0              0.0           150.0      1975.0
2024-01-09 09:23:00     113.0        75.0              0.0            75.0      2050.0
2024-01-09 09:24:00     115.0       150.0              0.0           150.0      2200.0
2024-01-09 09:25:00     105.0      -750.0              0.0          -750.0      1450.0
2024-01-09 09:26:00     102.0      -225.0              0.0          -225.0      1225.0
2024-01-09 09:27:00     100.0      -150.0              0.0          -150.0      1075.0
2024-01-09 09:28:00     101.5       112.5              0.0           112.5      1187.5
2024-01-09 09:29:00     102.5        75.0              0.0            75.0      1262.5
2024-01-09 09:30:00     100.0      -187.5             50.0          -237.5      1025.0
```
`price` : In points  
`gross_step_pnl` : `current_price - previous_price` x `lot_size` x `num_lots`  (Signed by : `trade_type`)  
`transaction_cost` : positive transaction amount (in ₹) paid as `per_lot_transaction_cost` X `num_lots` at start and end of position, else 0.  
`net_step_pnl` : `gross_step_pnl - transaction_cost` replace NaN by 0.  
`pnl` : Cumulative sum of `net_step_pnl`