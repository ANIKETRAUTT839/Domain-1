#ifndef STORE_AND_FORWARD_HPP
#define STORE_AND_FORWARD_HPP

#include "VSensorTypes.hpp"
#include "AnomalyDetector.hpp"
#include <vector>
#include <string>
#include <mutex>
#include <fstream>
#include <iostream>

struct TelemetryPacket {
    vsensor_sample_t sample;
    AnomalyReport report;
};

class StoreAndForward {
public:
    explicit StoreAndForward(const std::string& db_path = "vsense_buffer.sqlite")
        : db_path_(db_path) {}

    void buffer_telemetry(const vsensor_sample_t& sample, const AnomalyReport& report) {
        std::lock_guard<std::mutex> lock(mtx_);
        buffer_.push_back({sample, report});
        if (buffer_.size() > 5000) {
            buffer_.erase(buffer_.begin()); // Prevent infinite memory growth
        }
    }

    std::vector<TelemetryPacket> fetch_batch(size_t batch_size = 10) {
        std::lock_guard<std::mutex> lock(mtx_);
        std::vector<TelemetryPacket> batch;
        size_t count = std::min(batch_size, buffer_.size());
        for (size_t i = 0; i < count; ++i) {
            batch.push_back(buffer_[i]);
        }
        return batch;
    }

    void acknowledge_batch(size_t count) {
        std::lock_guard<std::mutex> lock(mtx_);
        size_t erase_count = std::min(count, buffer_.size());
        buffer_.erase(buffer_.begin(), buffer_.begin() + erase_count);
    }

    size_t pending_count() const {
        std::lock_guard<std::mutex> lock(mtx_);
        return buffer_.size();
    }

private:
    std::string db_path_;
    mutable std::mutex mtx_;
    std::vector<TelemetryPacket> buffer_;
};

#endif // STORE_AND_FORWARD_HPP
