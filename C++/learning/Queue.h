#include <iostream>

#ifndef QUEUE_H
#define QUEUE_H

template <class Item>
class Queue {
    enum {Q_SIZE = 10};
private:
    struct Node {Item item; struct Node *next;};
    Node *front;
    Node *rear;
    int items;
    const int qsize;
    
public:
    Queue(int qs = Q_SIZE);
    ~Queue();
    bool isempty() const;
    bool isfull() const;
    int queuecount() const;
    bool enqueue(const Item &item);
    bool dequeue(Item &item);
};
#endif