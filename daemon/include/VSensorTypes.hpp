#ifndef VSENSOR_TYPES_HPP
#define VSENSOR_TYPES_HPP

#include <cstdint>
#include <string>

#define MAGIC_HEADER 0x56534E53

#pragma pack(push, 1)
struct vsensor_sample_t {
    uint32_t magic;         // 0x56534E53
    uint32_t sensor_id;     // 1 to 6
    uint32_t sensor_type;   // 1 to 6
    double   value;         // sensor reading
    uint64_t timestamp_ns;  // UTC nanoseconds
    uint64_t seq_num;       // Monotonic sequence number
    uint16_t status_flags;  // Bitmask
    uint16_t crc16;         // CRC16 checksum
};
#pragma pack(pop)

enum class DeviceState {
    NORMAL,
    WARNING,
    CRITICAL,
    RECOVERY
};

inline std::string device_state_to_string(DeviceState state) {
    switch (state) {
        case DeviceState::NORMAL:   return "NORMAL";
        case DeviceState::WARNING:  return "WARNING";
        case DeviceState::CRITICAL: return "CRITICAL";
        case DeviceState::RECOVERY: return "RECOVERY";
        default: return "UNKNOWN";
    }
}

inline std::string get_sensor_name(uint32_t id) {
    switch (id) {
        case 1: return "Temperature";
        case 2: return "Humidity";
        case 3: return "Pressure";
        case 4: return "Vibration";
        case 5: return "Voltage";
        case 6: return "Current";
        default: return "Sensor_" + std::to_string(id);
    }
}

inline std::string get_sensor_unit(uint32_t id) {
    switch (id) {
        case 1: return "°C";
        case 2: return "%";
        case 3: return "hPa";
        case 4: return "mm/s";
        case 5: return "V";
        case 6: return "A";
        default: return "";
    }
}

#endif // VSENSOR_TYPES_HPP
