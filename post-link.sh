FILE_NAME="cet-auto.sh"
FILE="$HOME/.cet/$FILE_NAME"
PYTHON_LIB_PATH="$PREFIX/lib/python3."
if [ -L "$FILE" ] ; then
    if [ ! -e "$FILE" ] ; then
        for PYTHON_MINOR_VERSION in `seq 6 10`; do
            if [ -d "$PYTHON_LIB_PATH$PYTHON_MINOR_VERSION" ]; then
                break
            fi
            PYTHON_MINOR_VERSION=$((PYTHON_MINOR_VERSION+1))
        done
        ln -fs "$PYTHON_LIB_PATH$PYTHON_MINOR_VERSION/site-packages/cet/shell/$FILE_NAME" "$FILE"
    fi
fi
