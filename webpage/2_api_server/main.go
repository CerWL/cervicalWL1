package main

import (
	configs "./configs"
	logger "./log"
	"./routes"

	"fmt"
	"net"
	"net/http"
	"os"
	"syscall"
	"time"

	"github.com/fvbock/endless"
)

func atexit() {
}

func printlistenaddr(port string) {
	addrs, err := net.InterfaceAddrs()
	if err != nil {
		panic(err)
	}
	for _, address := range addrs {
		if ipnet, ok := address.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			if ipnet.IP.To4() != nil {
				logger.Warning.Printf("http://%s%s", ipnet.IP.String(), port)
			}
		}
	}
}

func main() {
	release := os.Getenv("RELEASE")
	r := routes.Router()

	port := configs.Server.Port
	endPoint := fmt.Sprintf(":%d", port)
	printlistenaddr(endPoint)

	defer atexit()

	if release != "true" {
		logger.Info.Printf("port on ==> %d", port)
		if err := http.ListenAndServe(endPoint, r); err != nil {
			logger.Error.Fatal(err)
		}
	} else {
		endless.DefaultReadTimeOut = 1 * time.Second
		endless.DefaultWriteTimeOut = 1 * time.Second
		endless.DefaultMaxHeaderBytes = 1 << 20

		server := endless.NewServer(endPoint, r)
		server.BeforeBegin = func(add string) {
			logger.Info.Printf("Actual pid is %d", syscall.Getpid())
		}

		logger.Info.Printf("port on ==> %d", port)

		err := server.ListenAndServe()
		if err != nil {
			logger.Error.Fatal("Server err: %v", err)
		}
	}
}