package main

import (
    "fmt"
    "os"
    "strings"
)

type Server struct {
    host string
    port int
}

func NewServer(host string, port int) *Server {
    return &Server{host: host, port: port}
}

func (s *Server) Start() error {
    fmt.Printf("Starting server on %s:%d\n", s.host, s.port)
    return nil
}

func main() {
    srv := NewServer("localhost", 8080)
    if err := srv.Start(); err != nil {
        fmt.Fprintf(os.Stderr, "error: %v\n", err)
        os.Exit(1)
    }
}
