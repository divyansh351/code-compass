"""Unit tests for TreeSitterAnalyzer multi-language parsing (JS/TS, Go, Rust, Java, C/C++)."""

from pathlib import Path
import pytest

from compass.analyzers.treesitter import TreeSitterAnalyzer


def test_treesitter_typescript_analysis(tmp_path: Path):
    """Test extracting TypeScript classes, methods, functions, calls, and imports."""
    ts_code = """
import { Injectable } from '@nestjs/common';
import axios from 'axios';

export class PaymentService extends BaseService {
    private client: any;

    constructor() {
        super();
        this.client = axios.create();
    }

    async processPayment(amount: number, currency: string): Promise<boolean> {
        const validated = this.validateAmount(amount);
        const result = await this.client.post('/pay', { amount, currency });
        return result.status === 200;
    }

    validateAmount(amt: number): boolean {
        return amt > 0;
    }
}

export function createService(): PaymentService {
    return new PaymentService();
}
"""
    file_path = tmp_path / "payment.ts"
    file_path.write_text(ts_code, encoding="utf-8")

    analyzer = TreeSitterAnalyzer("typescript")
    assert analyzer.supports("typescript")
    assert analyzer.can_analyze(file_path)

    res = analyzer.analyze_file(file_path, "src/payment.ts")
    assert res.language == "typescript"

    # Symbols
    sym_names = [s.name for s in res.symbols]
    assert "PaymentService" in sym_names
    assert "processPayment" in sym_names
    assert "validateAmount" in sym_names
    assert "createService" in sym_names

    # Inheritance
    assert len(res.inheritances) >= 1
    assert res.inheritances[0].superclass_name == "BaseService"

    # Imports
    mod_names = [i.module for i in res.imports]
    assert any("@nestjs/common" in m for m in mod_names)
    assert any("axios" in m for m in mod_names)

    # Function/Method Calls
    callee_names = [c.callee_name for c in res.calls]
    assert any("axios.create" in c or "create" in c for c in callee_names)
    assert any("validateAmount" in c for c in callee_names)


def test_treesitter_go_analysis(tmp_path: Path):
    """Test extracting Go structs, functions, methods, imports, and calls."""
    go_code = """
package main

import (
    "fmt"
    "net/http"
)

type Server struct {
    port int
}

func (s *Server) Start() error {
    fmt.Println("Starting server...")
    return http.ListenAndServe(fmt.Sprintf(":%d", s.port), nil)
}

func NewServer(port int) *Server {
    return &Server{port: port}
}
"""
    file_path = tmp_path / "server.go"
    file_path.write_text(go_code, encoding="utf-8")

    analyzer = TreeSitterAnalyzer("go")
    res = analyzer.analyze_file(file_path, "server.go")

    sym_names = [s.name for s in res.symbols]
    assert "Server" in sym_names
    assert "Start" in sym_names
    assert "NewServer" in sym_names

    # Imports
    mod_names = [i.module for i in res.imports]
    assert "fmt" in mod_names
    assert "net/http" in mod_names

    # Calls
    callee_names = [c.callee_name for c in res.calls]
    assert any("Println" in c or "fmt.Println" in c for c in callee_names)


def test_treesitter_rust_analysis(tmp_path: Path):
    """Test extracting Rust structs, functions, imports, and calls."""
    rs_code = """
use std::net::TcpListener;
use std::io::Write;

pub struct AppConfig {
    pub host: String,
    pub port: u16,
}

pub fn run_server(config: AppConfig) {
    let addr = format!("{}:{}", config.host, config.port);
    let listener = TcpListener::bind(addr).unwrap();
    println!("Server running");
}
"""
    file_path = tmp_path / "main.rs"
    file_path.write_text(rs_code, encoding="utf-8")

    analyzer = TreeSitterAnalyzer("rust")
    res = analyzer.analyze_file(file_path, "src/main.rs")

    sym_names = [s.name for s in res.symbols]
    assert "AppConfig" in sym_names
    assert "run_server" in sym_names

    # Imports
    mod_names = [i.module for i in res.imports]
    assert any("TcpListener" in m for m in mod_names)

    # Calls
    callee_names = [c.callee_name for c in res.calls]
    assert any("bind" in c or "TcpListener::bind" in c or "println" in c for c in callee_names)
