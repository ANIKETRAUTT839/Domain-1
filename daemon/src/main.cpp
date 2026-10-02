#include "VSensorTypes.hpp"
#include "ThreadSafeQueue.hpp"
#include "Validator.hpp"
#include "AnomalyDetector.hpp"
#include "StoreAndForward.hpp"
#include "CloudClient.hpp"

#include <iostream>
#include <fstream>
#include <thread>
#include <chrono>
#include <atomic>
#include <csignal>

std::atomic<bool> g_running(true);

void signal_handler(int signum) {
    std::cout << "\n[VSENSORD] Received signal " << signum << ". Shutting down..." << std::endl;
    g_running = false;
}

int main(int argc, char* argv[]) {
    std::string device_path = "/tmp/vsensor0";
    if (argc > 1) device_path = argv[1];

    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    std::cout << "=============================================" << std::endl;
    std::cout << "  VSense-HIL Telemetry Daemon (vsensord)     " << std::endl;
    std::cout << "  Device Node: " << device_path << std::endl;
    std::cout << "=============================================" << std::endl;

    ThreadSafeQueue<vsensor_sample_t> queue(1000);
    Validator validator;
    AnomalyDetector anomaly_engine;
    StoreAndForward storage("vsense_buffer.sqlite");
    CloudClient cloud_client;

    // Reader Thread
    std::thread reader_thread([&]() {
        while (g_running) {
            std::ifstream dev(device_path, std::ios::binary);
            if (!dev.is_open()) {
                std::this_thread::sleep_for(std::chrono::milliseconds(500));
                continue;
            }

            vsensor_sample_t sample;
            while (g_running && dev.read(reinterpret_cast<char*>(&sample), sizeof(vsensor_sample_t))) {
                queue.push(sample);
            }
        }
    });

    // Processor Thread
    std::thread processor_thread([&]() {
        uint64_t processed_count = 0;
        while (g_running || !queue.empty()) {
            vsensor_sample_t sample;
            if (queue.pop(sample)) {
                auto val_res = validator.validate(sample);
                if (!val_res.is_valid) {
                    std::cerr << "[VALIDATOR ERROR] Sample #" << sample.seq_num << ": " << val_res.error_message << std::endl;
                    continue;
                }

                auto report = anomaly_engine.process_sample(sample);
                storage.buffer_telemetry(sample, report);
                processed_count++;

                if (processed_count % 10 == 0) {
                    auto batch = storage.fetch_batch(10);
                    if (cloud_client.send_batch(batch)) {
                        storage.acknowledge_batch(batch.size());
                    }
                }
            }
        }
    });

    if (reader_thread.joinable()) reader_thread.join();
    queue.shutdown();
    if (processor_thread.joinable()) processor_thread.join();

    std::cout << "[VSENSORD] Daemon shutdown complete." << std::endl;
    return 0;
}
