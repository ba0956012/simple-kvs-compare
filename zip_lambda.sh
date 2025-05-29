BUILD_DIR="lambda_build"
ZIP_FILE="lambda.zip"

# 清理舊資料
rm -rf $BUILD_DIR $ZIP_FILE
mkdir $BUILD_DIR

# 安裝依賴
pip install -r requirements.txt -t $BUILD_DIR

# 複製原始碼與模板
cp -r app $BUILD_DIR/
cp -r templates $BUILD_DIR/
cp lambda_function.py $BUILD_DIR/
cp .env $BUILD_DIR/
cp normalize_params.json $BUILD_DIR/

# 進入目錄打包
cd $BUILD_DIR
zip -r ../$ZIP_FILE .
cd ..

# 完成
echo "✅ 打包完成：$ZIP_FILE"
