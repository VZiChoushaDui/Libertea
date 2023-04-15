#!/bin/bash

LANGUAGES=(zh fa)
for lang in "${LANGUAGES[@]}"; do
    rm -f README-$lang.md
    echo "Translating README.md to README-$lang.md..."
    trans -s en -t $lang -i README.md -b --no-bidi -o README-$lang.md
done

sed -i 's/自由茶/Libertea/g' README-zh.md
sed -i 's/لیبرتی/Libertea/g' README-fa.md
