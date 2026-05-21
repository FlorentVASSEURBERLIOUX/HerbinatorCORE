#!/bin/bash
cd ~/HerbinatorCORE

RC_TMP=$(mktemp)
cat ~/.bashrc > "$RC_TMP"
echo "source ~/HerbinatorCORE/env/bin/activate" >> "$RC_TMP"
echo "echo '======================================================='" >> "$RC_TMP"
echo "echo ' Environnement lancé ! (env)'" >> "$RC_TMP"
echo "echo ' Tapez 'exit' pour sortir.'" >> "$RC_TMP"
echo "echo '======================================================='" >> "$RC_TMP"
echo "rm -f \"\$RC_TMP\"" >> "$RC_TMP" 

exec bash --rcfile "$RC_TMP"
