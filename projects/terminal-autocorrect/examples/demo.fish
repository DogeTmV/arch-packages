#!/usr/bin/env fish
# Safe demo: explains decisions without running or changing anything.
set -l script (path resolve (path dirname (status filename))/../autocorrect.sh)

for word in lss lst sl pakman frobnicat rrm sduo
    printf '\n--- %s ---\n' "$word"
    bash "$script" explain $word
end
