#ifndef THREAD_SAFE_QUEUE_HPP
#define THREAD_SAFE_QUEUE_HPP

#include <queue>
#include <mutex>
#include <condition_variable>
#include <cstddef>

template <typename T>
class ThreadSafeQueue {
public:
    explicit ThreadSafeQueue(size_t max_capacity = 1000)
        : max_capacity_(max_capacity), shutdown_(false) {}

    bool push(const T& item) {
        std::unique_lock<std::mutex> lock(mtx_);
        if (queue_.size() >= max_capacity_) {
            // Queue full: drop oldest element to maintain low latency
            queue_.pop();
        }
        queue_.push(item);
        lock.unlock();
        cv_.notify_one();
        return true;
    }

    bool pop(T& item) {
        std::unique_lock<std::mutex> lock(mtx_);
        cv_.wait(lock, [this] { return !queue_.empty() || shutdown_; });
        if (shutdown_ && queue_.empty()) {
            return false;
        }
        item = queue_.front();
        queue_.pop();
        return true;
    }

    void shutdown() {
        std::unique_lock<std::mutex> lock(mtx_);
        shutdown_ = true;
        lock.unlock();
        cv_.notify_all();
    }

    size_t size() const {
        std::lock_guard<std::mutex> lock(mtx_);
        return queue_.size();
    }

    bool empty() const {
        std::lock_guard<std::mutex> lock(mtx_);
        return queue_.empty();
    }

private:
    std::queue<T> queue_;
    mutable std::mutex mtx_;
    std::condition_variable cv_;
    size_t max_capacity_;
    bool shutdown_;
};

#endif // THREAD_SAFE_QUEUE_HPP
