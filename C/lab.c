#include <stdio.h>

#define MAXN 1000005

int pi[MAXN];       
int min[MAXN]; 
char s[MAXN];         

int main() {
    int k;
    scanf("%d", &k);

    scanf("%s", s + 1);

    pi[1] = 0;
    for (int i = 2, j = 0; i <= k; i++) {
        while (j > 0 && s[i] != s[j + 1]) {
            j = pi[j];
        }
        if (s[i] == s[j + 1]) {
            j++;
        }
        pi[i] = j;
    }

    long long total_max = 0;

    for (int i = 1; i <= k; i++) {
        int longest = pi[i];
        
        if (longest == 0) {
            min[i] = 0;
        } else {
            // 记忆化逻辑：
            // 如果最长 border 还有更短的 border，直接继承它的结果
            // 否则，最长 border 就是最短 border
            if (min[longest] > 0) {
                min[i] = min[longest];
            } else {
                min[i] = longest;
            }
            
            // 最大周期长度 = 当前长度 - 最短 Border 长度
            total_max += (i - min[i]);
        }
    }

    // 3. 输出结果 (使用 lld 输出 long long)
    printf("%lld\n", total_max);

    return 0;
}