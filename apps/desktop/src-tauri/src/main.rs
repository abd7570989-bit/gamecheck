// Release builds on Windows run without an extra console window.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    gamecheck_lib::run()
}
