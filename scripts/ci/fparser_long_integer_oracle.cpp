// Native GMP-integer oracle for the fparser long-integer differential.
//
// Build with FP_SUPPORT_GMP_INT_TYPE; reads one expression per line,
// evaluates it with FunctionParser_gmpint at x = 5 and prints the result.

#include "fparser_gmpint.hh"

#include <iostream>
#include <string>

int main()
{
    FunctionParser_gmpint parser;
    std::string line;
    while (std::getline(std::cin, line))
    {
        if (line.empty())
            continue;
        if (parser.Parse(line, "x") >= 0)
        {
            std::cout << "PARSE_ERROR\n";
            continue;
        }
        GmpInt x(5);
        std::cout << parser.Eval(&x).getAsString() << '\n';
    }
    return 0;
}
