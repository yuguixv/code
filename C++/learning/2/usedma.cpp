#include <iostream>
#include "dma.h"

int main(){
    baseDMA rs1("rs1", 5);
    lacksDMA rs2("red", "rs2", 3);
    hasDMA rs3("style3", "rs3", 4);

    std::cout << rs1 << std::endl;
    std::cout << rs2 << std::endl;
    std::cout << rs3 << std::endl;

    return 0;
}