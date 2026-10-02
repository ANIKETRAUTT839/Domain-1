#ifndef ANOMALY_DETECTOR_HPP
#define ANOMALY_DETECTOR_HPP

#include "VSensorTypes.hpp"
#include <vector>
#include <deque>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <mutex>
#include <map>

struct AnomalyReport {
    double z_score;
    double moving_avg;
    DeviceState state;
    bool is_anomaly;
    std::string alert_severity; // "INFO", "WARNING", "CRITICAL"
    std::string alert_message;
};

class AnomalyDetector {
public:
    explicit AnomalyDetector(size_t window_size = 30)
        : window_size_(window_size), current_state_(DeviceState::NORMAL), consecutive_valid_(0), consecutive_anomalies_(0) {}

    AnomalyReport process_sample(const vsensor_sample_t& sample) {
        std::lock_guard<std::mutex> lock(mtx_);

        auto& window = windows_[sample.sensor_id];
        window.push_back(sample.value);
        if (window.size() > window_size_) {
            window.pop_front();
        }

        double sum = std::accumulate(window.begin(), window.end(), 0.0);
        double mean = sum / window.size();

        double sq_sum = 0.0;
        for (double val : window) {
            sq_sum += (val - mean) * (val - mean);
        }
        double stddev = std::sqrt(sq_sum / window.size());

        double z_score = 0.0;
        if (stddev > 0.0001) {
            z_score = (sample.value - mean) / stddev;
        }

        bool is_anomaly = (std::abs(z_score) > 2.5) || ((sample.status_flags & 0x1E) != 0);

        // State Machine Logic
        if (is_anomaly) {
            consecutive_valid_ = 0;
            consecutive_anomalies_++;

            if (std::abs(z_score) > 4.0 || consecutive_anomalies_ >= 3 || (sample.status_flags & 0x10)) {
                current_state_ = DeviceState::CRITICAL;
            } else if (current_state_ == DeviceState::NORMAL) {
                current_state_ = DeviceState::WARNING;
            }
        } else {
            consecutive_anomalies_ = 0;
            consecutive_valid_++;

            if (current_state_ == DeviceState::CRITICAL && consecutive_valid_ >= 5) {
                current_state_ = DeviceState::RECOVERY;
            } else if (current_state_ == DeviceState::RECOVERY && consecutive_valid_ >= 10) {
                current_state_ = DeviceState::NORMAL;
            } else if (current_state_ == DeviceState::WARNING && consecutive_valid_ >= 5) {
                current_state_ = DeviceState::NORMAL;
            }
        }

        std::string severity = "INFO";
        std::string msg = "Normal operating baseline";

        if (current_state_ == DeviceState::CRITICAL) {
            severity = "CRITICAL";
            msg = "Critical anomaly detected! Z-score: " + std::to_string(z_score);
        } else if (current_state_ == DeviceState::WARNING) {
            severity = "WARNING";
            msg = "Elevated signal variance. Z-score: " + std::to_string(z_score);
        } else if (current_state_ == DeviceState::RECOVERY) {
            severity = "INFO";
            msg = "Device stabilizing towards recovery baseline";
        }

        return {z_score, mean, current_state_, is_anomaly, severity, msg};
    }

    DeviceState get_state() const {
        std::lock_guard<std::mutex> lock(mtx_);
        return current_state_;
    }

    void reset_state() {
        std::lock_guard<std::mutex> lock(mtx_);
        current_state_ = DeviceState::NORMAL;
        consecutive_valid_ = 0;
        consecutive_anomalies_ = 0;
    }

private:
    size_t window_size_;
    mutable std::mutex mtx_;
    std::map<uint32_t, std::deque<double>> windows_;
    DeviceState current_state_;
    int consecutive_valid_;
    int consecutive_anomalies_;
};

#endif // ANOMALY_DETECTOR_HPP
