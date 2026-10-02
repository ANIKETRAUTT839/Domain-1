#ifndef CLOUD_CLIENT_HPP
#define CLOUD_CLIENT_HPP

#include "StoreAndForward.hpp"
#include <string>
#include <vector>
#include <iostream>
#include <sstream>

class CloudClient {
public:
    CloudClient(const std::string& endpoint = "http://localhost:8000/api/v1/telemetry",
                const std::string& api_key = "vsense_secret_api_key_12345")
        : endpoint_(endpoint), api_key_(api_key) {}

    bool send_batch(const std::vector<TelemetryPacket>& batch) {
        if (batch.empty()) return true;

        std::stringstream json;
        json << "{\"device_id\":\"vsense-edge-01\",\"batch_size\":" << batch.size() << ",\"telemetry\":[";
        for (size_t i = 0; i < batch.size(); ++i) {
            const auto& item = batch[i];
            json << "{"
                 << "\"sensor_id\":" << item.sample.sensor_id << ","
                 << "\"name\":\"" << get_sensor_name(item.sample.sensor_id) << "\","
                 << "\"type\":\"" << get_sensor_name(item.sample.sensor_id) << "\","
                 << "\"value\":" << item.sample.value << ","
                 << "\"unit\":\"" << get_sensor_unit(item.sample.sensor_id) << "\","
                 << "\"timestamp_ns\":" << item.sample.timestamp_ns << ","
                 << "\"seq_num\":" << item.sample.seq_num << ","
                 << "\"status_flags\":" << item.sample.status_flags << ","
                 << "\"state\":\"" << device_state_to_string(item.report.state) << "\","
                 << "\"z_score\":" << item.report.z_score << ","
                 << "\"alert_severity\":\"" << item.report.alert_severity << "\","
                 << "\"alert_message\":\"" << item.report.alert_message << "\""
                 << "}";
            if (i + 1 < batch.size()) json << ",";
        }
        json << "]}";

        return post_http(json.str());
    }

private:
    bool post_http(const std::string& payload) {
        // Uses curl command or socket HTTP request for portable execution
        std::string command = "curl -s -X POST \"" + endpoint_ + "\" "
                              "-H \"Content-Type: application/json\" "
                              "-H \"X-API-Key: " + api_key_ + "\" "
                              "-d '" + payload + "' > /dev/null 2>&1";
#ifdef _WIN32
        // On Windows PowerShell / cmd
        command = "powershell -Command \"Invoke-RestMethod -Uri '" + endpoint_ + "' -Method Post -Headers @{'Content-Type'='application/json'; 'X-API-Key'='" + api_key_ + "'} -Body '" + payload.substr(0, payload.length()) + "' | Out-Null\"";
#endif
        int ret = system(command.c_str());
        return (ret == 0);
    }

    std::string endpoint_;
    std::string api_key_;
};

#endif // CLOUD_CLIENT_HPP
