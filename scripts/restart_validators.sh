#!/bin/bash
cd ~/queryagent
source .venv/bin/activate

# Kill old validators
kill $(pgrep -f validator_local) 2>/dev/null
sleep 2

NETUID=3
CHAIN="ws://127.0.0.1:9944"
mkdir -p /tmp/validator_logs

for i in 1 2 3; do
    nohup python3 -m neurons.validator_local \
        --netuid $NETUID \
        --wallet.name "validator_$i" \
        --wallet.hotkey default \
        --subtensor.network "$CHAIN" \
        > /tmp/validator_logs/validator_${i}.log 2>&1 &
    echo "validator_$i PID $!"
done

sleep 10
echo "Validators running: $(pgrep -f validator_local | wc -l)"
tail -15 /tmp/validator_logs/validator_1.log
