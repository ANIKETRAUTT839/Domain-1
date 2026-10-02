/*
 * Linux Kernel Character Driver: vsensor.c
 * Target: /dev/vsensor0 Virtual Sensor Device Driver
 * Exposes hrtimer sample generation, ring buffer, wait queues, ioctl, and procfs.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/uaccess.h>
#include <linux/spinlock.h>
#include <linux/hrtimer.h>
#include <linux/ktime.h>
#include <linux/wait.h>
#include <linux/poll.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/device.h>

#define DEVICE_NAME "vsensor0"
#define CLASS_NAME "vsensor"
#define RING_BUFFER_SIZE 128
#define MAGIC_HEADER 0x56534E53

/* ioctl definitions */
#define VSENSOR_IOC_MAGIC 'v'
#define VSENSOR_IOC_SET_RATE      _IOW(VSENSOR_IOC_MAGIC, 1, unsigned int)
#define VSENSOR_IOC_SELECT_SENSOR _IOW(VSENSOR_IOC_MAGIC, 2, unsigned int)
#define VSENSOR_IOC_RESET         _IO(VSENSOR_IOC_MAGIC, 3)
#define VSENSOR_IOC_GET_STATUS    _IOR(VSENSOR_IOC_MAGIC, 4, unsigned int[4])

#pragma pack(push, 1)
typedef struct {
    u32 magic;
    u32 sensor_id;
    u32 sensor_type;
    double value;
    u64 timestamp_ns;
    u64 seq_num;
    u16 status_flags;
    u16 crc16;
} vsensor_sample_t;
#pragma pack(pop)

static int major_num;
static struct class *vsensor_class = NULL;
static struct device *vsensor_device = NULL;
static struct cdev vsensor_cdev;

/* Ring Buffer */
static vsensor_sample_t ring_buffer[RING_BUFFER_SIZE];
static int buffer_head = 0;
static int buffer_tail = 0;
static spinlock_t buffer_lock;
static DECLARE_WAIT_QUEUE_HEAD(read_wait);

/* Driver Control */
static u32 sample_rate_hz = 5;
static u32 selected_sensor = 0; /* 0 = All */
static u64 sample_counter = 0;
static u64 dropped_samples = 0;
static struct hrtimer sample_timer;
static ktime_t timer_interval;

/* Procfs */
static struct proc_dir_entry *proc_entry;

/* CRC Calculation */
static u16 compute_crc16(const unsigned char *data, size_t len) {
    u16 crc = 0xFFFF;
    size_t i, j;
    for (i = 0; i < len; i++) {
        crc ^= data[i];
        for (j = 0; j < 8; j++) {
            if (crc & 0x0001)
                crc = (crc >> 1) ^ 0xA001;
            else
                crc >>= 1;
        }
    }
    return crc & 0xFFFF;
}

/* Timer callback */
static enum hrtimer_restart timer_callback(struct hrtimer *timer) {
    vsensor_sample_t sample;
    unsigned long flags;
    u64 now_ns = ktime_get_real_ns();

    sample.magic = MAGIC_HEADER;
    sample.sensor_id = (selected_sensor > 0) ? selected_sensor : ((sample_counter % 6) + 1);
    sample.sensor_type = sample.sensor_id;
    sample.value = 25.0 + (double)(sample_counter % 50) / 10.0;
    sample.timestamp_ns = now_ns;
    sample.seq_num = ++sample_counter;
    sample.status_flags = 0x01;
    sample.crc16 = compute_crc16((unsigned char *)&sample, sizeof(vsensor_sample_t) - sizeof(u16));

    spin_lock_irqsave(&buffer_lock, flags);
    int next_head = (buffer_head + 1) % RING_BUFFER_SIZE;
    if (next_head != buffer_tail) {
        ring_buffer[buffer_head] = sample;
        buffer_head = next_head;
    } else {
        dropped_samples++;
    }
    spin_unlock_irqrestore(&buffer_lock, flags);

    wake_up_interruptible(&read_wait);

    hrtimer_forward_now(timer, timer_interval);
    return HRTIMER_RESTART;
}

/* File operations */
static int vsensor_open(struct inode *inodep, struct file *filep) {
    return 0;
}

static int vsensor_release(struct inode *inodep, struct file *filep) {
    return 0;
}

static ssize_t vsensor_read(struct file *filep, char __user *buffer, size_t len, loff_t *offset) {
    vsensor_sample_t sample;
    unsigned long flags;
    int err;

    if (len < sizeof(vsensor_sample_t))
        return -EINVAL;

    spin_lock_irqsave(&buffer_lock, flags);
    while (buffer_head == buffer_tail) {
        spin_unlock_irqrestore(&buffer_lock, flags);
        if (filep->f_flags & O_NONBLOCK)
            return -EAGAIN;
        if (wait_event_interruptible(read_wait, buffer_head != buffer_tail))
            return -ERESTARTSYS;
        spin_lock_irqsave(&buffer_lock, flags);
    }

    sample = ring_buffer[buffer_tail];
    buffer_tail = (buffer_tail + 1) % RING_BUFFER_SIZE;
    spin_unlock_irqrestore(&buffer_lock, flags);

    err = copy_to_user(buffer, &sample, sizeof(vsensor_sample_t));
    if (err)
        return -EFAULT;

    return sizeof(vsensor_sample_t);
}

static __poll_t vsensor_poll(struct file *filep, poll_table *wait) {
    __poll_t mask = 0;
    unsigned long flags;

    poll_wait(filep, &read_wait, wait);

    spin_lock_irqsave(&buffer_lock, flags);
    if (buffer_head != buffer_tail)
        mask |= EPOLLIN | EPOLLRDNORM;
    spin_unlock_irqrestore(&buffer_lock, flags);

    return mask;
}

static long vsensor_ioctl(struct file *filep, unsigned int cmd, unsigned long arg) {
    unsigned long flags;
    u32 rate, sensor;
    u32 status[4];

    switch (cmd) {
        case VSENSOR_IOC_SET_RATE:
            if (copy_from_user(&rate, (u32 __user *)arg, sizeof(u32)))
                return -EFAULT;
            if (rate < 1 || rate > 1000)
                return -EINVAL;
            sample_rate_hz = rate;
            timer_interval = ktime_set(0, 1000000000 / sample_rate_hz);
            break;

        case VSENSOR_IOC_SELECT_SENSOR:
            if (copy_from_user(&sensor, (u32 __user *)arg, sizeof(u32)))
                return -EFAULT;
            selected_sensor = sensor;
            break;

        case VSENSOR_IOC_RESET:
            spin_lock_irqsave(&buffer_lock, flags);
            buffer_head = 0;
            buffer_tail = 0;
            sample_counter = 0;
            dropped_samples = 0;
            spin_unlock_irqrestore(&buffer_lock, flags);
            break;

        case VSENSOR_IOC_GET_STATUS:
            status[0] = (u32)sample_counter;
            status[1] = (u32)dropped_samples;
            status[2] = (u32)buffer_head;
            status[3] = (u32)buffer_tail;
            if (copy_to_user((u32 __user *)arg, status, sizeof(status)))
                return -EFAULT;
            break;

        default:
            return -ENOTTY;
    }
    return 0;
}

static struct file_operations fops = {
    .owner = THIS_MODULE,
    .open = vsensor_open,
    .release = vsensor_release,
    .read = vsensor_read,
    .poll = vsensor_poll,
    .unlocked_ioctl = vsensor_ioctl,
};

/* Procfs handler */
static int proc_show(struct seq_file *m, void *v) {
    seq_printf(m, "VSense-HIL Kernel Driver Status\n");
    seq_printf(m, "Sample Rate: %u Hz\n", sample_rate_hz);
    seq_printf(m, "Selected Sensor: %u\n", selected_sensor);
    seq_printf(m, "Total Samples: %llu\n", sample_counter);
    seq_printf(m, "Dropped Samples: %llu\n", dropped_samples);
    return 0;
}

static int proc_open(struct inode *inode, struct file *file) {
    return single_open(file, proc_show, NULL);
}

static const struct proc_ops proc_fops = {
    .proc_open = proc_open,
    .proc_read = seq_read,
    .proc_lseek = seq_lseek,
    .proc_release = single_release,
};

static int __init vsensor_init(void) {
    int ret;
    dev_t dev;

    spin_lock_init(&buffer_lock);

    ret = alloc_chrdev_region(&dev, 0, 1, DEVICE_NAME);
    major_num = MAJOR(dev);
    if (ret < 0) return ret;

    cdev_init(&vsensor_cdev, &fops);
    vsensor_cdev.owner = THIS_MODULE;
    ret = cdev_add(&vsensor_cdev, dev, 1);
    if (ret < 0) goto unregister_chrdev;

    vsensor_class = class_create(CLASS_NAME);
    if (IS_ERR(vsensor_class)) {
        ret = PTR_ERR(vsensor_class);
        goto del_cdev;
    }

    vsensor_device = device_create(vsensor_class, NULL, dev, NULL, DEVICE_NAME);
    if (IS_ERR(vsensor_device)) {
        ret = PTR_ERR(vsensor_device);
        goto destroy_class;
    }

    proc_entry = proc_create("vsensor", 0444, NULL, &proc_fops);

    /* Setup hrtimer */
    timer_interval = ktime_set(0, 1000000000 / sample_rate_hz);
    hrtimer_init(&sample_timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
    sample_timer.function = timer_callback;
    hrtimer_start(&sample_timer, timer_interval, HRTIMER_MODE_REL);

    pr_info("VSense-HIL Driver Loaded: /dev/%s (major %d)\n", DEVICE_NAME, major_num);
    return 0;

destroy_class:
    class_destroy(vsensor_class);
del_cdev:
    cdev_del(&vsensor_cdev);
unregister_chrdev:
    unregister_chrdev_region(dev, 1);
    return ret;
}

static void __exit vsensor_exit(void) {
    hrtimer_cancel(&sample_timer);
    if (proc_entry) proc_remove(proc_entry);
    device_destroy(vsensor_class, MKDEV(major_num, 0));
    class_destroy(vsensor_class);
    cdev_del(&vsensor_cdev);
    unregister_chrdev_region(MKDEV(major_num, 0), 1);
    pr_info("VSense-HIL Driver Unloaded\n");
}

module_init(vsensor_init);
module_exit(vsensor_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("VSense-HIL Embedded Team");
MODULE_DESCRIPTION("Virtual Sensor HIL Character Device Driver");
MODULE_VERSION("1.0");
