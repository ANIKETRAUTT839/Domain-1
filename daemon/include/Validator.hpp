#ifndef VALIDATOR_HPP
#define VALIDATOR_HPP

#include "VSensorTypes.hpp"
#include <cmath>
#include <map>
#include <cstddef>

struct ValidationResult {
    bool is_valid;
    std::string error_message;
};

class Validator {
public:
    static uint16_t compute_crc16(const uint8_t* data, size_t len) {
        uint16_t crc = 0xFFFF;
        for (size_t i = 0; i < len; ++i) {
            crc ^= data[i];
            for (int j = 0; j < 8; ++j) {
                if (crc & 0x0001)
                    crc = (crc >> 1) ^ 0xA001;
                else
                    crc = crc >> 1;
            }
        }
        return crc & 0xFFFF;
    }

    ValidationResult validate(const vsensor_sample_t& sample) {
        if (sample.magic != MAGIC_HEADER) {
            return {false, "Invalid magic header"};
        }

        if (std::isnan(sample.value) || std::isinf(sample.value)) {
            return {false, "NaN or Inf sensor reading"};
        }

        if (sample.sensor_id < 1 || sample.sensor_id > 6) {
            return {false, "Unknown sensor_id out of range [1..6]"};
        }

        // Verify CRC
        uint16_t expected_crc = compute_crc16(
            reinterpret_cast<const uint8_t*>(&sample),
            sizeof(vsensor_sample_t) - sizeof(uint16_t)
        );

        if (sample.crc16 != expected_crc) {
            return {false, "CRC16 checksum mismatch"};
        }

        // Sequence monotonicity check
        auto it = last_seq_map_.find(sample.sensor_id);
        if (it != last_seq_map_.end()) {
            if (sample.seq_num <= it->second) {
                return {false, "Sequence number gap or out of order"};
            }
        }
        last_seq_map_[sample.sensor_id] = sample.seq_num;

        return {true, "OK"};
    }

private:
    std::map<uint32_t, uint64_t> last_seq_map_;
};

#endif // VALIDATOR_HPP
