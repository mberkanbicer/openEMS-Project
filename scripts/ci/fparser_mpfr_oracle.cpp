// Native MPFR oracle for the fparser differential.
//
// Build with FP_SUPPORT_MPFR_FLOAT_TYPE; reads one expression per line,
// evaluates it with the native FunctionParser_mpfr at x = 0.5 and prints 30
// significant decimal digits.

#include "fparser_mpfr.hh"

#include <iostream>
#include <string>

int main()
{
    FunctionParser_mpfr parser;
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
        MpfrFloat x(0.5);
        std::cout << parser.Eval(&x).getAsString(30) << '\n';
    }
    return 0;
}
