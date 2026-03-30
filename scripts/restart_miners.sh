#!/bin/bash
cd ~/queryagent
source .venv/bin/activate

# Kill old miners
kill $(pgrep -f miner_local) 2>/dev/null
sleep 3
echo "Old miners killed"

NETUID=3
CHAIN="ws://127.0.0.1:9944"
mkdir -p /tmp/miner_logs

# Miners 1-3: strong (all tasks — easy + medium + hard)
# Miners 4-7: medium (easy + medium only)
# Miners 8-10: weak (easy only)
for i in $(seq 1 10); do
    PORT=$((8090 + $i))

    if [ $i -le 3 ]; then
        SKILL="strong"
    elif [ $i -le 7 ]; then
        SKILL="medium"
    else
        SKILL="weak"
    fi

    nohup python3 -m neurons.miner_local \
        --netuid $NETUID \
        --wallet.name "miner_$i" \
        --wallet.hotkey default \
        --subtensor.network "$CHAIN" \
        --axon.port $PORT \
        --skill $SKILL \
        > /tmp/miner_logs/miner_${i}.log 2>&1 &
    echo "  miner_$i on port $PORT [$SKILL] (PID $!)"
done

sleep 5
echo "Miners alive: $(pgrep -f miner_local | wc -l)"
