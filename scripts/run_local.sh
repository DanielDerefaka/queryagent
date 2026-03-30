#!/bin/bash
# Deploy script: kills old processes, starts miners + validators on local chain
set -e

cd ~/queryagent
source .venv/bin/activate

# Kill any old miners/validators
pkill -f "neurons.miner" 2>/dev/null || true
pkill -f "neurons.validator" 2>/dev/null || true
sleep 2

NETUID=3
CHAIN="ws://127.0.0.1:9944"

# Create log dirs
mkdir -p /tmp/miner_logs /tmp/validator_logs

echo "=== Starting 10 miners ==="
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

echo ""
echo "=== Starting 3 validators ==="
for i in $(seq 1 3); do
    nohup python3 -m neurons.validator_local \
        --netuid $NETUID \
        --wallet.name "validator_$i" \
        --wallet.hotkey default \
        --subtensor.network "$CHAIN" \
        > /tmp/validator_logs/validator_${i}.log 2>&1 &
    echo "  validator_$i (PID $!)"
done

sleep 5
echo "Validators alive: $(pgrep -f validator_local | wc -l)"
echo ""
echo "=== All processes launched ==="
echo "Check logs:"
echo "  tail -f /tmp/miner_logs/miner_1.log"
echo "  tail -f /tmp/validator_logs/validator_1.log"
