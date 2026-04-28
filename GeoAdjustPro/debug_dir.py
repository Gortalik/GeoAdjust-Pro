import os
print("Current working directory:", os.getcwd())
print("Files in current directory:")
for item in os.listdir('.'):
    print("  ", item)
    
print("\nChecking if src exists:")
print("os.path.isdir('src'):", os.path.isdir('src'))

if os.path.isdir('src'):
    print("Files in src:")
    for item in os.listdir('src'):
        print("  ", item)
        
    if os.path.isdir('src/geoadjust'):
        print("Files in src/geoadjust:")
        for item in os.listdir('src/geoadjust'):
            print("  ", item)
            
        if os.path.isdir('src/geoadjust/io'):
            print("Files in src/geoadjust/io:")
            for item in os.listdir('src/geoadjust/io'):
                print("  ", item)
                
            if os.path.isdir('src/geoadjust/io/formats'):
                print("Files in src/geoadjust/io/formats:")
                for item in os.listdir('src/geoadjust/io/formats'):
                    print("  ", item)