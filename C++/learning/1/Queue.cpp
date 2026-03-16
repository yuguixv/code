#include "Queue.h"

template <class Item>
Queue<Item>::Queue(int qs) : qsize(qs) {
    front = rear = NULL;
    items = 0;
}

template <class Item>
Queue<Item>::~Queue() {
    Node *temp;
    while(front != NULL){
        temp = front;
        front = front->next;
        delete temp;
    }
}

template <class Item>
bool Queue<Item>::isempty() const {
    return items == 0;
}

template <class Item>
bool Queue<Item>::isfull() const {
    return items == qsize;
}

template <class Item>
bool Queue<Item>::enqueue(const Item &item){
    if(isfull())
        return false;
    Node *add = new Node;
    add->item = item;
    add->next = nullptr;
    items++;
    if(front == 0)
        front = add;
    else
        rear->next = add;
    rear = add;
    return true;
}

template <class Item>
bool Queue<Item>::dequeue(Item &item){
    if(isempty())
        return false;
    item = front->item;
    items--;
    Node *temp = front;
    front = temp->next;
    delete temp;
    if(items == 0)
        rear = nullptr;
    return true;
}

