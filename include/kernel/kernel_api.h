/**
 * CS452ROTOS unified kernel API contract.
 * Byte-identical across all OS repos; implementations may differ per line
 * (APU / SMP / PrimeOS) as long as these signatures are satisfied.
 */
#ifndef KERNEL_API_H
#define KERNEL_API_H

#include <stdint.h>

/* --- Scheduler ---------------------------------------------------------- */

/** Initialize ready-queue heap and blocked-list metadata. */
void sched_init(void *stack_reg);

/** Enqueue a runnable task (legacy name: scrSchedule). */
void sched_enqueue(int pid, uint8_t priority);

/** Pick highest-priority ready task; returns PID or -1 if empty. */
int sched_pick(void);

/** Move a task off the ready queue into blocked state. */
void sched_block(int pid, uint8_t priority);

/**
 * Unblock a task by pid/priority if it is blocked.
 * @return 0 on success, non-zero if the task was not blocked.
 */
int sched_unblock(int pid, uint8_t priority);

/**
 * Compare two (priority, enqueue-time) pairs for heap ordering.
 * @return 1 if a runs before b, 2 if b before a, 0 if equal.
 */
uint8_t sched_compare_priority(uint8_t a_pri, uint64_t a_time,
                               uint8_t b_pri, uint64_t b_time);

/** Unblock all tasks waiting on an interrupt event. */
int sched_unblock_event(uint32_t interrupt_id, uint64_t ret);

/** Rescue runnable tasks lost from the ready heap (SMP idle recovery). */
void sched_rescue_orphans(void);

/* --- IPC (user syscalls) ------------------------------------------------ */

int ipc_send(int tid, const char *msg, int msglen, char *reply, int replylen);
int ipc_receive(int *tid, char *msg, int msglen);
int ipc_reply(int tid, const void *reply, int replylen);

/* --- IPC (kernel syscall handlers) -------------------------------------- */

void ipc_kernel_send(void);
void ipc_kernel_receive(int recv_tid);
void ipc_kernel_reply(void);

/* --- Core kernel ops ---------------------------------------------------- */

int kernel_create(uint8_t priority, void (*fn)(void), int parent);
void kernel_schedule(void);
int kernel_await_event(int event_id);
int kernel_my_core_id(void);

/* --- OS-specific hooks (weak defaults) ---------------------------------- */

void kernel_init_extras(void *reg);
void kernel_mailbox_notify(int dest_core, int slot);

#endif /* KERNEL_API_H */
