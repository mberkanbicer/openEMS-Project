// Native long-double oracle for the fparser differential.
//
// Build with FP_SUPPORT_LONG_DOUBLE_TYPE and FP_USE_STRTOLD; reads one
// expression per line, evaluates it with the native FunctionParser_ld at
// x = 0.5 and prints the f64 projection used for the comparison.

#include "fparser.hh"

#include <iomanip>
#include <iostream>
#include <string>

int main()
{
    FunctionParser_ld parser;
    std::string line;
    while (std::getline(std::cin, line))
    {
        if (line.empty())
            continue;
        if (parser.Parse(line, "x") >= 0)
        {
            std::cout << "ERROR\n";
            continue;
        }
        long double x = 0.5L;
        long double value = parser.Eval(&x);
        std::cout << std::scientific << std::setprecision(21)
                  << static_cast<double>(value) << '\n';
    }
    return 0;
}
