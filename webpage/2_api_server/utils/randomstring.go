package util

import (
	"crypto/md5"
	"encoding/hex"
	"math/rand"
	"time"
)

// MD5 生成32位MD5
func MD5(text string) string {
	ctx := md5.New()
	ctx.Write([]byte(text))
	return hex.EncodeToString(ctx.Sum(nil))
}

// GetRandomSalt return len=8  salt
func GetRandomSalt() string {
	return GetRandomString(8)
}

// GetRandomString 生成随机字符串
func GetRandomString(length int64) string {
	str := "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
	bytes := []byte(str)
	result := []byte{}
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	for i := 0; i < int(length); i++ {
		result = append(result, bytes[r.Intn(len(bytes))])
	}
	return string(result)
}

// GetRandomStringNum 生成随机字符串, 只包含数字
func GetRandomStringNum(length int64) string {
	str := "0123456789"
	bytes := []byte(str)
	result := []byte{}
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	for i := 0; i < int(length); i++ {
		result = append(result, bytes[r.Intn(len(bytes))])
	}
	return string(result)
}
